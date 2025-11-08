"""
Async UI Updates - Helpers for non-blocking UI operations.

Provides QThread-based workers for long-running operations to prevent UI freezing.
"""

import logging
import traceback
from typing import Any, Callable, Optional
from dataclasses import dataclass

try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QThread = object
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Result from a worker thread."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class Worker(QThread):
    """
    Generic worker thread for long-running operations.
    
    Signals:
        started: Emitted when work starts
        finished: Emitted when work completes (WorkerResult)
        progress: Emitted with progress updates (current, total, message)
        error: Emitted when an error occurs (error_message)
    """
    
    started = pyqtSignal()
    finished = pyqtSignal(object)  # WorkerResult
    progress = pyqtSignal(int, int, str)  # current, total, message
    error = pyqtSignal(str)
    
    def __init__(self, func: Callable, *args, **kwargs):
        """
        Initialize worker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_running = False
        self._should_stop = False
    
    def run(self):
        """Execute the worker function."""
        self._is_running = True
        self.started.emit()
        
        result = WorkerResult(success=False)
        
        try:
            logger.debug(f"Worker started: {self.func.__name__}")
            
            # Execute the function
            return_value = self.func(*self.args, **self.kwargs)
            
            result.success = True
            result.result = return_value
            
            logger.debug(f"Worker completed: {self.func.__name__}")
            
        except Exception as e:
            logger.error(f"Worker error in {self.func.__name__}: {e}", exc_info=True)
            result.success = False
            result.error = str(e)
            result.traceback = traceback.format_exc()
            self.error.emit(str(e))
        
        finally:
            self._is_running = False
            self.finished.emit(result)
    
    def stop(self):
        """Request the worker to stop."""
        self._should_stop = True
    
    def should_stop(self) -> bool:
        """Check if worker should stop."""
        return self._should_stop
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._is_running
    
    def emit_progress(self, current: int, total: int, message: str = ""):
        """
        Emit progress update.
        
        Args:
            current: Current progress
            total: Total items
            message: Progress message
        """
        self.progress.emit(current, total, message)


class AsyncTaskManager(QObject):
    """
    Manages async tasks with worker threads.
    
    Features:
    - Task queuing
    - Progress tracking
    - Cancellation support
    - Error handling
    
    Example:
        manager = AsyncTaskManager()
        
        def long_task():
            # Do something time-consuming
            return "result"
        
        worker = manager.run_async(long_task)
        worker.finished.connect(lambda r: print(r.result))
    """
    
    def __init__(self):
        super().__init__()
        self._workers = []
        self._active_workers = {}
        logger.info("Async task manager initialized")
    
    def run_async(
        self,
        func: Callable,
        *args,
        on_finished: Optional[Callable[[WorkerResult], None]] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        task_name: Optional[str] = None,
        **kwargs
    ) -> Worker:
        """
        Run a function asynchronously.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            on_finished: Callback when task finishes
            on_progress: Callback for progress updates
            on_error: Callback for errors
            task_name: Optional task identifier
            **kwargs: Keyword arguments for func
            
        Returns:
            Worker instance
        """
        worker = Worker(func, *args, **kwargs)
        
        # Connect callbacks
        if on_finished:
            worker.finished.connect(on_finished)
        
        if on_progress:
            worker.progress.connect(on_progress)
        
        if on_error:
            worker.error.connect(on_error)
        
        # Track worker
        self._workers.append(worker)
        if task_name:
            self._active_workers[task_name] = worker
        
        # Auto-cleanup
        def cleanup():
            if worker in self._workers:
                self._workers.remove(worker)
            if task_name and task_name in self._active_workers:
                del self._active_workers[task_name]
        
        worker.finished.connect(cleanup)
        
        # Start worker
        worker.start()
        
        logger.debug(f"Started async task: {task_name or func.__name__}")
        return worker
    
    def cancel_task(self, task_name: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_name: Name of task to cancel
            
        Returns:
            True if task was found and cancelled
        """
        if task_name in self._active_workers:
            worker = self._active_workers[task_name]
            worker.stop()
            worker.quit()
            worker.wait(1000)  # Wait up to 1 second
            logger.info(f"Cancelled task: {task_name}")
            return True
        return False
    
    def cancel_all(self):
        """Cancel all running tasks."""
        for worker in self._workers[:]:
            worker.stop()
            worker.quit()
            worker.wait(1000)
        
        self._workers.clear()
        self._active_workers.clear()
        logger.info("Cancelled all tasks")
    
    def get_active_tasks(self) -> list[str]:
        """Get list of active task names."""
        return list(self._active_workers.keys())
    
    def is_task_running(self, task_name: str) -> bool:
        """Check if a task is running."""
        return task_name in self._active_workers


# Global task manager instance
_task_manager: Optional[AsyncTaskManager] = None


def get_task_manager() -> AsyncTaskManager:
    """
    Get the global async task manager (singleton).
    
    Returns:
        Global AsyncTaskManager instance
    """
    global _task_manager
    
    if _task_manager is None:
        if PYQT6_AVAILABLE:
            _task_manager = AsyncTaskManager()
        else:
            # Return a dummy manager if PyQt6 not available
            class DummyManager:
                def run_async(self, *args, **kwargs):
                    logger.warning("PyQt6 not available, running synchronously")
                    func = args[0]
                    result = func(*args[1:], **kwargs)
                    return result
                
                def cancel_task(self, task_name):
                    return False
                
                def cancel_all(self):
                    pass
            
            _task_manager = DummyManager()
    
    return _task_manager


def run_async(
    func: Callable,
    *args,
    on_finished: Optional[Callable[[WorkerResult], None]] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
    task_name: Optional[str] = None,
    **kwargs
) -> Worker:
    """
    Convenient function to run a task asynchronously.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        on_finished: Callback when finished
        on_progress: Callback for progress
        on_error: Callback for errors
        task_name: Optional task identifier
        **kwargs: Keyword arguments
        
    Returns:
        Worker instance
        
    Example:
        def process_data(data):
            # Long operation
            return result
        
        worker = run_async(
            process_data,
            my_data,
            on_finished=lambda r: print(r.result),
            task_name="data_processing"
        )
    """
    manager = get_task_manager()
    return manager.run_async(
        func,
        *args,
        on_finished=on_finished,
        on_progress=on_progress,
        on_error=on_error,
        task_name=task_name,
        **kwargs
    )
