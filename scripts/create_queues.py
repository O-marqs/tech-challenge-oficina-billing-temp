"""Local emulator bootstrap only; shared AWS queues remain owned by team infra."""

import json
import os

import boto3


def create(client):
    for name in ["oficina-billing-comandos", "oficina-os-saga-respostas"]:
        dlq = client.create_queue(QueueName=name + "-dlq.fifo", Attributes={"FifoQueue": "true"})[
            "QueueUrl"
        ]
        arn = client.get_queue_attributes(QueueUrl=dlq, AttributeNames=["QueueArn"])["Attributes"][
            "QueueArn"
        ]
        client.create_queue(
            QueueName=name + ".fifo",
            Attributes={
                "FifoQueue": "true",
                "VisibilityTimeout": "30",
                "RedrivePolicy": json.dumps({"deadLetterTargetArn": arn, "maxReceiveCount": "5"}),
            },
        )


if __name__ == "__main__":
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "")
    if not endpoint or not any(
        name in endpoint for name in ["localhost", "localstack", "127.0.0.1"]
    ):
        raise SystemExit("This bootstrap is restricted to a configured local emulator endpoint")
    create(
        boto3.client(
            "sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"), endpoint_url=endpoint
        )
    )
