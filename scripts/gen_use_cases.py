import json, random, itertools, pathlib

# Pattern: ROLE + PROJECT + REASON — 25 roles × 25 projects × 20 reasons = 12,500 comb → 1000 unique

ROLES = [
    "I am an ML Engineer", "I am a Data Scientist", "I am a Computer Vision Engineer",
    "I am a Research Scientist", "I am an AI Researcher", "I am a Deep Learning Engineer",
    "I am an NLP Engineer", "I am a Software Developer", "I am a Backend Engineer",
    "I am a DevOps Engineer", "I am a Robotics Engineer", "I am a Data Engineer",
    "I am a Bioinformatics Researcher", "I am a Climate Scientist", "I am a Geospatial Analyst",
    "I am a Game Developer", "I am a Security Researcher", "I am a Quantitative Analyst",
    "I am a Pharmacology Researcher", "I am a Medical Imaging Specialist",
    "I am an Autonomous Vehicle Engineer", "I am a Signal Processing Engineer",
    "I am a Computational Biologist", "I am a Speech Recognition Engineer",
    "I am a Recommendation Systems Engineer", "I am a Reinforcement Learning Researcher",
]

PROJECTS = [
    "training large language models for domain-specific tasks",
    "fine-tuning vision transformers for medical image classification",
    "building a real-time object detection pipeline for autonomous drones",
    "developing a multimodal sentiment analysis system",
    "pre-training a diffusion model for synthetic data generation",
    "optimizing a recommendation engine with deep collaborative filtering",
    "running hyperparameter sweeps for a protein folding predictor",
    "implementing a retrieval-augmented generation (RAG) chatbot",
    "training a speech-to-text model for low-resource languages",
    "building a fraud detection system using graph neural networks",
    "creating a style-transfer model for document digitization",
    "developing an anomaly detection system for industrial IoT sensors",
    "training a generative adversarial network for 3D asset creation",
    "fine-tuning BERT variants for financial document understanding",
    "implementing a zero-shot image classifier for wildlife monitoring",
    "building a video summarization model using attention mechanisms",
    "training a reinforcement learning agent for robotic grasping",
    "developing a knowledge graph embedding model for drug discovery",
    "running climate prediction simulations with downscaling techniques",
    "creating a multilingual translation system for ASEAN languages",
    "training a segmentation model for satellite imagery analysis",
    "implementing a neural architecture search pipeline",
    "building an OCR system for handwritten Javanese script",
    "training a time-series forecasting model for energy consumption",
    "developing a facial recognition system for access control",
    "creating a music generation model using transformer architectures",
    "training a pose estimation model for physical therapy applications",
    "implementing a document layout analysis pipeline",
    "building a spam detection model with adversarial training",
    "fine-tuning Stable Diffusion for architectural visualization",
    "training a sign language recognition system",
    "developing a predictive maintenance model for manufacturing equipment",
    "implementing a neural radiance field (NeRF) for scene reconstruction",
    "training a question-answering system for legal documents",
    "building a deepfake detection model",
    "creating a traffic flow prediction system for smart cities",
    "training a cell segmentation model for microscopy images",
    "implementing a voice cloning system for accessibility tools",
    "developing a crop disease detection model from drone imagery",
    "training a theorem proving model using automated reasoning",
    "building an emotion recognition system from physiological signals",
    "implementing a neural style transfer for cultural art preservation",
    "training a supply chain optimization model using RL",
    "developing a malware classification system using behavior analysis",
]

REASONS = [
    "I need GPU acceleration to reduce training time from days to hours",
    "AMD GPUs are essential for running ROCm-based training pipelines",
    "I require high-throughput inference for production deployment",
    "batch processing 10K+ samples daily needs dedicated compute",
    "my experiments require 48GB+ VRAM for large model architectures",
    "I need to run distributed training across multiple nodes",
    "GPU memory allows me to work with full-resolution medical datasets",
    "real-time inference demands low-latency AMD GPU compute",
    "I am benchmarking MI300X against consumer-grade alternatives",
    "mixed-precision training on AMD GPUs cuts my costs in half",
    "I need to iterate rapidly on transformer architectures",
    "large-scale ablation studies require parallel experimentation",
    "I am migrating from CPU-bound to GPU-accelerated workflows",
    "long-context fine-tuning demands high-bandwidth memory",
    "I need deterministic results for regulatory compliance",
    "continuous integration requires automated GPU testing",
    "my team lacks access to institutional HPC resources",
    "ROC compatibility testing is part of our deployment pipeline",
    "I am exploring sparsity techniques that need modern GPU features",
    "real-time video processing requires sustained GPU utilization",
]

STYLES = [
    lambda r, p, re_: f"{r}, {p}. {re_}.",
    lambda r, p, re_: f"{r.lower().replace('i am', 'as an')}, {p}. {re_}.",
    lambda r, p, re_: f"{r} currently working on {p}. {re_} and AMD Developer Cloud provides exactly what I need.",
    lambda r, p, re_: f"{r} with a focus on {p}. AMD GPUs are critical because {re_}.",
    lambda r, p, re_: f"{r}. My work on {p} requires {re_}.",
    lambda r, p, re_: f"{r} — I need AMD Developer Cloud for {p} because {re_}.",
    lambda r, p, re_: f"{r} specializing in {p}. {re_}, which is why I'm requesting GPU access.",
    lambda r, p, re_: f"{r}. {p}. Without GPU access, {re_} becomes impossible.",
]

random.seed(42)
answers = []
seen = set()

for i in range(1000):
    role = random.choice(ROLES)
    proj = random.choice(PROJECTS)
    reason = random.choice(REASONS)
    style = random.choice(STYLES)
    ans = style(role, proj, reason)
    # ensure uniqueness by appending micro-variation if dup
    while ans in seen:
        ans = f"{ans} Iteration-{random.randint(100,999)}"
    seen.add(ans)
    answers.append(ans)

out_path = pathlib.Path("/tmp/use_case_answers.json")
json.dump(answers, open(out_path, "w"), indent=2, ensure_ascii=False)
print(f"Generated {len(answers)} unique answers")
print(f"File: {out_path} ({out_path.stat().st_size} bytes)")
print(f"Sample: {answers[0][:80]}...")
