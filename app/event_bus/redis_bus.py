import asyncio
import json
from typing import Callable, Dict, Optional

import redis.asyncio as redis

from app.config import config
from app.logger import logger


class RedisEventBus:
    def __init__(self):
        self.redis_host = config.redis.host
        self.redis_port = config.redis.port
        self.redis_db = config.redis.db
        self.redis_password = getattr(config.redis, 'password', None)
        self.stream_max_len = getattr(config.redis, 'event_stream_max_len', 1000)

        self.redis_client: Optional[redis.Redis] = None
        self._stop_event = asyncio.Event()
        self._consumer_tasks: list[asyncio.Task] = []
        self._subscriptions: Dict[str, Dict[str, Callable]] = {} # stream_name -> {group_consumer_key -> callback}

    async def connect(self):
        if self.redis_client and self.redis_client.is_connected:
            logger.info("Redis client already connected.")
            return
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True # Important for handling strings easily
            )
            await self.redis_client.ping()
            logger.info(f"Successfully connected to Redis at {self.redis_host}:{self.redis_port}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            raise

    async def publish(self, stream_name: str, event_data: dict):
        if not self.redis_client:
            await self.connect()
        if not self.redis_client:
            logger.error("Cannot publish event, Redis client not connected.")
            return

        try:
            # Convert dict to JSON string if it's not already (though Redis client might handle dicts)
            # For safety, we'll ensure it's string key-value pairs for XADD.
            # Redis Python client's xadd typically expects a flat dictionary of field-value pairs.
            # If event_data is complex, we might need to serialize the whole thing as one field.
            # Let's assume event_data is a flat dict of strings for now, or serialize it.

            # Simplest approach: serialize the whole event_data to a JSON string and store it under a 'data' field.
            payload = {'data': json.dumps(event_data)}

            event_id = await self.redis_client.xadd(
                name=stream_name,
                fields=payload,
                maxlen=self.stream_max_len,
                approximate=True # Needed if maxlen is used
            )
            logger.info(f"Event {event_id} published to stream '{stream_name}': {event_data}")
            return event_id
        except Exception as e:
            logger.error(f"Error publishing event to stream '{stream_name}': {e}")
            return None

    async def _ensure_consumer_group(self, stream_name: str, group_name: str):
        if not self.redis_client:
            await self.connect()
        if not self.redis_client:
            logger.error("Cannot ensure consumer group, Redis client not connected.")
            return
        try:
            await self.redis_client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id='0',  # Start from the beginning of the stream
                mkstream=True # Create the stream if it doesn't exist
            )
            logger.info(f"Consumer group '{group_name}' ensured for stream '{stream_name}'.")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group '{group_name}' already exists for stream '{stream_name}'.")
            else:
                logger.error(f"Error creating/checking consumer group '{group_name}' for stream '{stream_name}': {e}")
                raise

    async def subscribe(self, stream_name: str, group_name: str, consumer_name: str, callback: Callable):
        if not self.redis_client:
            await self.connect()
        if not self.redis_client:
            logger.error("Cannot subscribe, Redis client not connected.")
            return

        await self._ensure_consumer_group(stream_name, group_name)

        subscription_key = f"{group_name}::{consumer_name}"
        if stream_name not in self._subscriptions:
            self._subscriptions[stream_name] = {}

        if subscription_key in self._subscriptions[stream_name]:
            logger.warning(f"Consumer '{consumer_name}' in group '{group_name}' already subscribed to stream '{stream_name}'. Overwriting callback.")
            # Potentially stop old task if callback is being replaced for an active consumer.
            # For simplicity now, we'll just overwrite.

        self._subscriptions[stream_name][subscription_key] = callback
        logger.info(f"Consumer '{consumer_name}' in group '{group_name}' subscribed to stream '{stream_name}'.")

        # If start_consuming has already been called, we might need to dynamically add this new consumer.
        # For now, assume subscriptions are set up before start_consuming.

    async def _consume_loop(self, stream_name: str, group_name: str, consumer_name: str, callback: Callable):
        logger.info(f"Starting consumer loop for stream '{stream_name}', group '{group_name}', consumer '{consumer_name}'")
        while not self._stop_event.is_set():
            try:
                if not self.redis_client or not self.redis_client.is_connected: # Check connection
                    logger.warning(f"Consumer {consumer_name}: Redis disconnected. Attempting to reconnect...")
                    await asyncio.sleep(5) # Wait before retrying
                    await self.connect()
                    if not self.redis_client: # Still not connected
                        logger.error(f"Consumer {consumer_name}: Reconnection failed. Stopping consumer.")
                        break
                    else: # Reconnected, ensure group again
                        await self._ensure_consumer_group(stream_name, group_name)


                # Read from the stream using the consumer group
                # '>' means get new messages for this consumer
                messages = await self.redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: '>'},
                    count=10, # Process up to 10 messages at a time
                    block=1000 # Block for 1 second waiting for messages
                )

                if not messages:
                    await asyncio.sleep(0.1) # Short sleep if no messages to prevent tight loop
                    continue

                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        event_id = msg_id
                        # Assuming payload was stored under 'data' field as JSON string
                        event_payload_json = msg_data.get('data')
                        if event_payload_json:
                            try:
                                event_payload = json.loads(event_payload_json)
                                logger.debug(f"Consumer '{consumer_name}' received event {event_id} from stream '{stream}': {event_payload}")
                                await callback(event_payload, event_id, stream_name, group_name, consumer_name)
                                # Acknowledge the message
                                await self.redis_client.xack(stream_name, group_name, event_id)
                                logger.debug(f"Event {event_id} acknowledged by consumer '{consumer_name}'.")
                            except json.JSONDecodeError as e_json:
                                logger.error(f"Consumer '{consumer_name}' failed to decode JSON for event {event_id}: {e_json}. Message data: {msg_data}")
                                # Decide on error handling: XACK, XAUTOCLAIM, DLQ? For now, log and potentially XACK to avoid reprocessing bad msg.
                                # To be safe, let's not XACK bad JSON for now, it will be re-delivered.
                            except Exception as e_cb:
                                logger.error(f"Consumer '{consumer_name}' error processing event {event_id} with callback: {e_cb}", exc_info=True)
                                # Error in callback, message will be redelivered to another consumer or this one after timeout.
                                # Consider a dead-letter queue or XACKing if errors are persistent.
                        else:
                            logger.warning(f"Consumer '{consumer_name}' received message {event_id} without 'data' field: {msg_data}")
                            await self.redis_client.xack(stream_name, group_name, event_id) # Acknowledge it to remove


            except redis.exceptions.TimeoutError: # From XREADGROUP block
                logger.debug(f"Consumer {consumer_name} for stream {stream_name}: No new messages, continuing.")
                continue # Timeout is expected, just continue loop
            except redis.exceptions.ConnectionError as e_conn:
                logger.error(f"Consumer {consumer_name}: Redis connection error: {e_conn}. Will attempt to reconnect.")
                await asyncio.sleep(5) # Wait before attempting to reconnect in the next iteration
            except Exception as e:
                logger.error(f"Consumer loop error for stream '{stream_name}', consumer '{consumer_name}': {e}", exc_info=True)
                await asyncio.sleep(1) # Avoid tight loop on unexpected errors
        logger.info(f"Exiting consumer loop for stream '{stream_name}', group '{group_name}', consumer '{consumer_name}'")

    def start_consuming(self):
        if not self._subscriptions:
            logger.warning("No subscriptions configured. Call subscribe() first.")
            return

        if self._consumer_tasks:
            logger.warning("Consumers already started.")
            return

        self._stop_event.clear() # Ensure stop_event is clear before starting

        for stream_name, group_consumers in self._subscriptions.items():
            for key, callback in group_consumers.items():
                group_name, consumer_name = key.split("::", 1)
                task = asyncio.create_task(self._consume_loop(stream_name, group_name, consumer_name, callback))
                self._consumer_tasks.append(task)

        logger.info(f"Started {len(self._consumer_tasks)} consumer task(s).")

    async def shutdown(self):
        logger.info("Shutting down RedisEventBus...")
        self._stop_event.set() # Signal all consumer loops to stop

        if self._consumer_tasks:
            logger.info(f"Waiting for {len(self._consumer_tasks)} consumer task(s) to complete...")
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
            self._consumer_tasks = []
            logger.info("All consumer tasks completed.")

        if self.redis_client:
            try:
                await self.redis_client.close()
                await self.redis_client.connection_pool.disconnect()
                logger.info("Redis client connection closed.")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
            finally:
                self.redis_client = None
        logger.info("RedisEventBus shutdown complete.")

# Global instance (optional, depends on how it's used in the app)
# event_bus = RedisEventBus()

async def example_event_handler(event_data, event_id, stream, group, consumer):
    logger.info(f"Handler [{consumer}@{group} on {stream}]: Received event {event_id} - {event_data}")
    # Simulate work
    await asyncio.sleep(0.1)

async def main_example():
    # This example assumes Redis is running on localhost:6379
    # And that config.redis section is available in your app.config

    bus = RedisEventBus()
    await bus.connect()

    # Subscribe two consumers to the same stream and group
    await bus.subscribe("mystream", "mygroup", "consumer1", example_event_handler)
    await bus.subscribe("mystream", "mygroup", "consumer2", example_event_handler)

    # Subscribe a consumer to a different stream
    await bus.subscribe("anotherstream", "anothergroup", "consumer_other", example_event_handler)

    bus.start_consuming()

    # Publish some events
    for i in range(5):
        await bus.publish("mystream", {"message": f"Hello from mystream! Event {i}", "count": i})
        await asyncio.sleep(0.05)

    for i in range(3):
        await bus.publish("anotherstream", {"data": f"Data for anotherstream {i}"})
        await asyncio.sleep(0.05)

    # Let consumers run for a bit
    await asyncio.sleep(5)

    # Publish more events
    await bus.publish("mystream", {"message": "One last event for mystream"})

    await asyncio.sleep(2)
    await bus.shutdown()

if __name__ == "__main__":
    # Setup basic logging for the example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Starting Redis Event Bus example...")

    # Example of how to add Redis config if not loaded from file
    # This is for standalone execution of this script.
    # In a real app, config would be loaded by app.config.Config()
    class MockRedisConfig:
        host = "localhost"
        port = 6379
        db = 0
        password = None
        event_stream_max_len = 1000

    class MockConfig:
        redis = MockRedisConfig()
        # Add other necessary config attributes if RedisEventBus depends on them directly or via logger
        # For example, if logger setup depends on config.PROJECT_ROOT:
        # PROJECT_ROOT = "." # Or an appropriate path

    # Temporarily override global config for this example if it's not already set
    if not hasattr(config, 'redis'):
        logger.warning("config.redis not found, using mock config for example.")
        setattr(config, 'redis', MockRedisConfig())
        # If other parts of config are needed by logger, set them too.

    asyncio.run(main_example())
    logger.info("Redis Event Bus example finished.")
