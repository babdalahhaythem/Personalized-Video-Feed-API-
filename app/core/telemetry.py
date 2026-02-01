"""
Telemetry configuration (Metrics & Tracing).
Sets up Prometheus instrumentation and OpenTelemetry.
"""
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings


def setup_telemetry(app: FastAPI) -> None:
    """
    Setup Observability (Metrics & Tracing).
    
    1. Prometheus Metrics via /metrics
    2. OpenTelemetry Tracing via OTLP
    """
    settings = get_settings()
    
    # -------------------------------------------------------------------------
    # 1. Prometheus Metrics
    # -------------------------------------------------------------------------
    if settings.ENABLE_PROMETHEUS:
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health", "/health/ready"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="inprogress",
            inprogress_labels=True,
        )
        instrumentator.instrument(app).expose(app, include_in_schema=False)
    
    # -------------------------------------------------------------------------
    # 2. OpenTelemetry Tracing
    # -------------------------------------------------------------------------
    if settings.ENABLE_OTEL:
        # Define resource (service name, version, etc.)
        resource = Resource.create(attributes={
            "service.name": settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": "production" if not settings.DEBUG else "development",
        })

        # Set up Tracer Provider
        provider = TracerProvider(resource=resource)
        
        # OTLP Exporter (sends traces to Jaeger/Tempo/Honeycomb)
        # Default is localhost:4317
        otlp_exporter = OTLPSpanExporter()
        
        # Batch processor for performance
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
