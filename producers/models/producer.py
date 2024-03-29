"""Producer base-class providing common utilites and functionality"""
import logging
import time


from confluent_kafka import avro
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.avro import AvroProducer

logger = logging.getLogger(__name__)


class Producer:
    """Defines and provides common functionality amongst Producers"""

    # Tracks existing topics across all Producer instances
    existing_topics = set([])

    def __init__(
        self,
        topic_name,
        key_schema,
        value_schema=None,
        num_partitions=1,
        num_replicas=1,
    ):
        """Initializes a Producer object with basic settings"""
        self.topic_name = topic_name
        self.key_schema = key_schema
        self.value_schema = value_schema
        self.num_partitions = num_partitions
        self.num_replicas = num_replicas

        #
        #
        # Configure the broker properties below. Make sure to reference the project README
        # and use the Host URL for Kafka and Schema Registry!
        #
        #
        self.broker_properties = {
            "bootstrap.servers": ",".join(["PLAINTEXT://localhost:9092", "PLAINTEXT://localhost:9093", "PLAINTEXT://localhost:9094"]),
            "schema.registry.url": "http://localhost:8081"
        }

        # If the topic does not already exist, try to create it
        if self.topic_name not in Producer.existing_topics:
            self.create_topic()
            Producer.existing_topics.add(self.topic_name)

        # Configure the AvroProducer
        self.producer = AvroProducer(
            self.broker_properties,
            default_key_schema=key_schema,
            default_value_schema=value_schema
        )

    def create_topic(self):
        """Creates the producer topic if it does not already exist"""
        logger.info("Creating topic %s", self.topic_name)
        client = AdminClient(
            {"bootstrap.servers": self.broker_properties["bootstrap.servers"]}
        )
        
        # Check if the topic is already created
        topic_exsists = self.check_topic_exists(client, self.topic_name)
        
        if (topic_exsists):
            logger.info("Topic %s already exist", self.topic_name)
            return

        logger.info(
            "Creating topic %s with %s partitions and %s replicas",
            self.topic_name, self.num_partitions, self.num_replicas
        )

        responses = client.create_topics([
            NewTopic(self.topic_name, self.num_partitions, self.num_replicas)
        ])

        for topic, response in responses.items():
            try:
                response.result()
                logger.info("Topic created")
            except Exception as e:
                logger.fatal("Failed creating topic %s: %s", topic, e)
    
    def close(self):
        """Prepares the producer for exit by cleaning up the producer"""
        if self.producer is not None:
            logger.debug("Flushing producer")
            self.producer.flush()

    def time_millis(self):
        """Use this function to get the key for Kafka Events"""
        return int(round(time.time() * 1000))
    
    def check_topic_exists(self, client, topic_name):
        """Checks if the given topic exists"""
        # Requesting metadata from cluster with max response_time=5 before timing out
        topic_metadata = client.list_topics(timeout=5)
        topics = topic_metadata.topics
        return topic_name in topics
