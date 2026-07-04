import logging
import typing

from aiokafka import AIOKafkaConsumer

from src.application.ports.usecases import IndexAdPort, RemoveAdPort

logger = logging.getLogger(__name__)


class KafkaAdsConsumer:
    def __init__(
        self,
        consumer: AIOKafkaConsumer,
        index_ad: IndexAdPort,
        remove_ad: RemoveAdPort,
    ) -> None:
        self._consumer = consumer
        self._index_ad = index_ad
        self._remove_ad = remove_ad

    async def run(self) -> None:
        async for msg in self._consumer:
            trace_id = None
            if msg.headers:
                for k, v in msg.headers:
                    if k == "x-trace-id":
                        trace_id = v.decode("utf-8")
                        break

            if not trace_id and isinstance(msg.value, dict):
                trace_id = msg.value.get("payload", {}).get("trace_id")

            if not trace_id:
                import uuid

                trace_id = str(uuid.uuid4())

            from src.infrastructure.logging import trace_id_var

            token = trace_id_var.set(trace_id)
            try:
                await self._handle(msg.value)
            except Exception:
                logger.exception("failed to handle message %s", msg)
                continue
            finally:
                trace_id_var.reset(token)
            await self._consumer.commit()

    async def _handle(self, value: dict[str, typing.Any]) -> None:
        event = value.get("event")
        payload = value.get("payload") or {}
        ad_id = payload.get("ad_id")
        if not isinstance(ad_id, int):
            logger.warning("skip message without ad_id: %s", value)
            return

        if event in ("ad.created", "ad.updated"):
            await self._index_ad.execute(ad_id)
        elif event == "ad.deleted":
            await self._remove_ad.execute(ad_id)
        else:
            logger.warning("unknown event type: %s", event)
