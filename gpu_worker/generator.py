import modal

app = modal.App("anychat-gpu-worker")

image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0", "huggingface_hub[hf_transfer]==0.36.0")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)

@app.cls(
    image=image,
    gpu="A10G",
    min_containers=1,
    max_containers=1,
    scaledown_window=60,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=600,
)
@modal.concurrent(max_inputs=20)
class GPUWorker:
    @modal.enter()
    async def start(self):
        from vllm import AsyncLLMEngine, AsyncEngineArgs
        from transformers import AutoTokenizer
        from settings import llm_settings, api_settings
        import os

        os.environ["HF_TOKEN"] = api_settings.hf_token
        self.engine = AsyncLLMEngine.from_engine_args(
            AsyncEngineArgs(
                model=llm_settings.model_name,
                enforce_eager=False,
                gpu_memory_utilization=llm_settings.gpu_memory_utilization,
            )
        )
        self.tokenizer = AutoTokenizer.from_pretrained(llm_settings.model_name)

    @modal.method()
    async def generate_tokens(self, prompt: str):
        from vllm import SamplingParams
        from uuid import uuid4
        from settings import llm_settings

        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        sampling_params = SamplingParams(max_tokens=llm_settings.max_tokens, temperature=llm_settings.temperature)
        request_id = str(uuid4())
        previous_text = ""
        async for output in self.engine.generate(
            formatted_prompt, sampling_params=sampling_params, request_id=request_id
        ):
            current_text = output.outputs[0].text
            new_token = current_text[len(previous_text):]
            previous_text = current_text
            yield f"data: {new_token}\n\n"

        yield "[Done]"