import time
import logging
import queue
from .task_queue import task_queue

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

def main_loop():
    """
    The main operational loop for JEMAI.
    This function will contain the core logic for listening to triggers,
    processing commands, and interacting with other modules.
    """
    logger.info("Starting JEMAI main loop...")
    try:
        while True:
            try:
                # Wait for a task to appear in the queue.
                # A timeout allows the loop to remain responsive to interrupts.
                task = task_queue.get(block=True, timeout=1)
                logger.info(f"--- NEW TASK RECEIVED ---")
                logger.info(f"Task: {task}")
                
                # TODO: Process the task with the AI model.
                # For example: response = ai.process_command(task)
                
            except queue.Empty:
                # This is expected when there are no tasks.
                # The loop will simply continue and check again.
                continue

    except KeyboardInterrupt:
        logger.info("Main loop stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)

if __name__ == '__main__':
    # This allows the main_loop to be run directly for testing if needed.
    main_loop()
