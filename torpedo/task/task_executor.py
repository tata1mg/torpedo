import asyncio

from ..exceptions import TaskExecutorException


class TaskExecutor:
    def __init__(self, tasks: list):
        self._tasks = tasks
        self._task_mapping = {}
        self._executable_tasks = []

    async def submit(self):
        self.build_task_mapping()
        tasks = self._executable_tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for index, result in enumerate(results):
            self._task_mapping[index].result = result

        return self._tasks

    def build_task_mapping(self):
        index = 0
        is_main_task_present = False

        for task in self._tasks:
            if task.is_main:
                is_main_task_present = True

            self._executable_tasks.append(task.func)
            self._task_mapping[index] = task
            index += 1

        if not is_main_task_present:
            raise TaskExecutorException(
                "Atleast one task should be main while submitting " "to executor"
            )
