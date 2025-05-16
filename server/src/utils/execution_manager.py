import asyncio
import os

SANDBOX_WORKDIR = '/home/sandboxuser/app'

def user_container_id():

    id = 0
    while True:
        id += 1
        yield id

container_id_gen = user_container_id()


class Execution():

    def __init__(self, is_script=False):
        self.is_script = is_script
        self.container_name = f"n-{next(container_id_gen)}"
        self.container_running = False  # Will be set True when container is running
        self.process = None
        self.pid = None
        self.process_ready_event = asyncio.Event()

        # Vars for communication with client
        self.output_buff = []
        self.return_code = None


    async def run(self, code=None, path=None, user_storage=None):

        if self.is_script:
            await self.run_script(code)
        else:
            await self.run_from_storage(path, user_storage)

    async def run_script(self, code) -> int:

        command = [
            "docker", "run", "-i",
            "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "--name", self.container_name,
            "python_runner",
            "/bin/bash", "-c",
            f"touch script.py && echo '{code}' > script.py && python3 -u script.py"
        ]
        
        async def run_process():
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            # await asyncio.sleep(0.1)  # Wait a bit for the process to start
            self.pid = await self.get_python_pid()
            print(self.pid)

            # Signal that the process is ready
            self.process_ready_event.set()


        self.container_running = True

        await asyncio.gather(
            run_process(),
            self.handle_output()
            # self.moniter_input_syscalls()
        )

        return self.process.returncode
    
    async def run_from_storage(self, path: str, user_storage: str) -> int:
        
        command = [
            "docker", "run", "-i",
            "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "-v", f"{os.path.abspath(user_storage)}:{SANDBOX_WORKDIR}:ro",
            "--name", self.container_name,
            "python_runner",
            "python3", "-u", path
        ]
        
        async def run_process():
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            await asyncio.sleep(0.1)  # Wait a bit for the process to start
            # print("\ncheck:", self.container_name, path)
            self.pid = await self.get_python_pid(code_path=path)

            # Signal that the process is ready
            self.process_ready_event.set()


        self.container_running = True

        await asyncio.gather(
            run_process(),
            self.handle_output(self.process),
            self.moniter_input_syscalls()
        )

        return self.process.returncode
    
    async def get_python_pid(self, code_path: str = 'script.py') -> int:
        """
        Use `docker exec` to retrieve the PID of the Python process inside the running container.
        """
        # Use `docker exec` to run `pgrep` to get Python execution process id
        print(code_path, self.container_name)
        command = f"docker exec {self.container_name} pgrep -f {code_path}"

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Read the output from the command
        pid = await process.stdout.readline()
        await process.wait()
        print(pid)

        pid_str = pid.strip().decode('utf-8')  # decode bytes to string
        if not pid_str:
            print(f"Error: No Python PID returned for container {self.container_name}.")
            return None

        try:
            return int(pid_str)  # Convert the PID string to an integer
        except ValueError:
            print(f"Error: Failed to convert PID '{pid_str}' to an integer.")
            return None
        
    async def handle_output(self):
        
        # Wait for the process to be ready before starting streaming
        await self.process_ready_event.wait()

        while True:
            chunk = await self.process.stdout.read(1024)
            if not chunk:
                break  # EOF reached
            
            print("output:", chunk)

            self.output_buff.append(chunk.decode())
        
        # Inform websocket_controller `stream output()` of exeuction finish
        self.output_buff.append(None)

        await self.process.wait()
        self.container_running = False
        self.process_ready_event.clear()
    
    async def moniter_input_syscalls(self):
        """
        Asynchronously checks if the process is blocked on input from stdin.
        """
        # Wait for the process to be ready before starting streaming
        await self.process_ready_event.wait()

        while self.container_running:

            command = f"docker exec {self.container_name} ps -o state= -p {self.pid}"

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            res = await process.stdout.readline()
            if res.decode().strip() == 'S':
                await self.handle_input()
            

    async def handle_input(self):
        """
        Asynchronously streams input to the running container's stdin.
        """
        await self.send(self.server_create_response(protocol.CODE_BLOCKED_INPUT, None))
    
        input = await self.handle_request(await self.recv())
        # input = (json.loads(data))['input']

        # Command to write to process's stdin in the container
        command = [
            "docker", "exec", "-i", self.container_name,
            "bash", "-c", f"cat > /proc/{self.pid}/fd/0"
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Make sure input ends with new-line
        if not input.endswith('\n'):
            input += '\n'

        # Send the input string
        await process.communicate(input.encode())