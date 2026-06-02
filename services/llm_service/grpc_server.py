import grpc
from concurrent import futures

import inference_pb2
import inference_pb2_grpc
from inference import engine, MODEL_VERSION


class InferenceServicer(inference_pb2_grpc.InferenceServiceServicer):
    def Predict(self, request, context):
        text, latency = engine.generate(request.input_text)
        return inference_pb2.PredictResponse(
            output=text, latency_ms=latency, model_version=MODEL_VERSION
        )

    def Health(self, request, context):
        status = "healthy" if engine.is_ready() else "degraded"
        return inference_pb2.HealthResponse(status=status)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    inference_pb2_grpc.add_InferenceServiceServicer_to_server(InferenceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
