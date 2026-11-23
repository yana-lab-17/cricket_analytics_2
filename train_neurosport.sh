#!/usr/bin/env bash
# ==============================================================================
# train_neurosport.sh
# Production Pre-Training & Post-Training Launcher for NeuroSport-Cricket LLM
# ==============================================================================

set -e

echo "======================================================================"
echo "🏏 STARTING NEUROSPORT-CRICKET LLM PRE-TRAINING"
echo "======================================================================"

CONFIG=${1:-base}
EPOCHS=${2:-5}
BATCH_SIZE=${3:-4}
GRAD_ACCUM=${4:-8}
LR=${5:-3e-4}

echo "Configuration: ${CONFIG}"
echo "Epochs:        ${EPOCHS}"
echo "Batch Size:    ${BATCH_SIZE} (Effective Batch Size: $((BATCH_SIZE * GRAD_ACCUM)))"
echo "Learning Rate: ${LR}"
echo "======================================================================"

python3 -m llm.training.pretrain \
    --config "${CONFIG}" \
    --epochs "${EPOCHS}" \
    --batch_size "${BATCH_SIZE}" \
    --grad_accum "${GRAD_ACCUM}" \
    --lr "${LR}"

echo "======================================================================"
echo "🎯 PRE-TRAINING COMPLETE! STARTING DPO COGNITIVE ALIGNMENT..."
echo "======================================================================"

python3 -c "
import torch
from llm.server import get_or_create_neurosport_engine
from llm.training.post_train import run_dpo_alignment

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model, tokenizer = get_or_create_neurosport_engine(config_name='${CONFIG}', device=device)
run_dpo_alignment(model, tokenizer, device=device)

torch.save({
    'model_state_dict': model.state_dict(),
    'config': model.config
}, 'llm/checkpoints/neurosport_aligned_final.pt')
print('✓ Successfully saved aligned model to llm/checkpoints/neurosport_aligned_final.pt')
"

echo "======================================================================"
echo "🤖 STARTING REINFORCEMENT LEARNING (GRPO) PHYSICS SELF-PLAY..."
echo "======================================================================"

python3 -c "
import torch
from llm.server import get_or_create_neurosport_engine
from llm.training.grpo_rl import GRPOTrainer

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model, tokenizer = get_or_create_neurosport_engine(
    config_name='${CONFIG}',
    checkpoint_path='llm/checkpoints/neurosport_aligned_final.pt',
    device=device
)
trainer = GRPOTrainer(model, tokenizer, group_size=4, device=device)
trainer.train_step(num_iterations=25)

torch.save({
    'model_state_dict': model.state_dict(),
    'config': model.config
}, 'llm/checkpoints/neurosport_rl_final.pt')
print('✓ Successfully saved RL self-learned model to llm/checkpoints/neurosport_rl_final.pt')
"

echo "======================================================================"
echo "🎉 NEUROSPORT-CRICKET PRODUCTION LLM READY FOR INFERENCE!"
echo "To test interactively, run: python3 -m llm.server --chat"
echo "======================================================================"

