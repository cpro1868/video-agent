from __future__ import annotations


class VideoAgentError(Exception):
    code = "VIDEO_AGENT_ERROR"
    exit_code = 1

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class InvalidArgumentError(VideoAgentError):
    code = "INVALID_ARGUMENT"


class UnsupportedUrlError(VideoAgentError):
    code = "UNSUPPORTED_URL"


class AuthRequiredError(VideoAgentError):
    code = "AUTH_REQUIRED_ERROR"


class NetworkError(VideoAgentError):
    code = "NETWORK_ERROR"


class ProxyTimeoutError(VideoAgentError):
    code = "PROXY_TIMEOUT"


class SubtitleParseError(VideoAgentError):
    code = "SUBTITLE_PARSE_ERROR"


class AsrRuntimeError(VideoAgentError):
    code = "ASR_RUNTIME_ERROR"


class CudaOomError(VideoAgentError):
    code = "CUDA_OOM_ERROR"


class LlmTimeoutError(VideoAgentError):
    code = "LLM_TIMEOUT"


class LlmSafetyRefusalError(VideoAgentError):
    code = "LLM_SAFETY_REFUSAL"


class OutputContractError(VideoAgentError):
    code = "OUTPUT_CONTRACT_ERROR"


class NotImplementedPipelineError(VideoAgentError):
    code = "PIPELINE_NOT_IMPLEMENTED"
