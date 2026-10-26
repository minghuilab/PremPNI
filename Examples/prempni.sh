#!/usr/bin/env bash
# Run from your working directory; results are saved in ./output.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
arguments=("$@")
has_sample_id=false
file_input=false
show_help=false
for ((i = 0; i < ${#arguments[@]}; i++)); do
  case "${arguments[i]}" in
    --sample-id)
      if ((i + 1 >= ${#arguments[@]})) || [[ "${arguments[i + 1]}" == --* ]] || [[ "${arguments[i + 1]}" =~ ^[[:space:]]*$ ]]; then
        printf '%s\n' 'Error: --sample-id requires a nonempty name.' >&2
        exit 2
      fi
      has_sample_id=true
      ;;
    --sample-id=*)
      if [[ "${arguments[i]#*=}" =~ ^[[:space:]]*$ ]]; then
        printf '%s\n' 'Error: --sample-id requires a nonempty name.' >&2
        exit 2
      fi
      has_sample_id=true
      ;;
    --input-json|--input-tsv|--input-json=*|--input-tsv=*) file_input=true ;;
    -h|--help|--version) show_help=true ;;
  esac
done
mkdir -p output
output_dir="$(cd output && pwd)"
if [[ "$has_sample_id" == false && "$file_input" == false && "$show_help" == false ]]; then
  mkdir -p "$output_dir/.sample_ids"
  assigned=false
  for ((attempt = 0; attempt < 10; attempt++)); do
    if [[ -r /proc/sys/kernel/random/uuid ]]; then
      IFS= read -r random_id < /proc/sys/kernel/random/uuid
    elif command -v uuidgen >/dev/null 2>&1; then
      random_id="$(uuidgen)"
    else
      printf -v random_id '%04x%04x%04x%04x' "$RANDOM" "$RANDOM" "$RANDOM" "$RANDOM"
    fi
    sample_id="sample_$(date +%Y%m%d_%H%M%S)_${random_id//-/}"
    if [[ -e "$output_dir/protein_dna/$sample_id" || -e "$output_dir/protein_rna/$sample_id" ]]; then
      continue
    fi
    if mkdir "$output_dir/.sample_ids/$sample_id" 2>/dev/null; then
      assigned=true
      break
    fi
  done
  if [[ "$assigned" != true ]]; then
    printf '%s\n' 'Error: could not reserve a new sample name.' >&2
    exit 2
  fi
  arguments+=(--sample-id "$sample_id")
  printf 'Sample ID: %s\n' "$sample_id" >&2
fi
mounts=(-v "$output_dir:/output" -v "$script_dir:/examples:ro")
if [[ -d input ]]; then
  input_dir="$(cd input && pwd)"
  mounts+=(-v "$input_dir:/input:ro")
fi
exec docker run --rm "${mounts[@]}" ghcr.io/minghuilab/prempni "${arguments[@]}"
