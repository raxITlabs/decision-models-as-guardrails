variable "project_id" {
  description = "Target GCP project. A dedicated project is recommended; shared projects need care with quota and cost."
  type        = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "env" {
  description = "Label only. dev | research | prod."
  type        = string
  default     = "dev"
}

variable "machine_type" {
  description = "g2-standard-24 carries two L4 GPUs (24 GB each), one per 9B model. g2-standard-8 carries one L4 and serves one 9B at a time."
  type        = string
  default     = "g2-standard-24"
}

variable "spot" {
  description = "Spot VMs are about a third of the on-demand price and can be preempted at any time; fine for a benchmark that writes receipts per row."
  type        = bool
  default     = true
}

variable "boot_disk_gb" {
  description = "Room for CUDA, two base models, and adapters. 200 GB is comfortable."
  type        = number
  default     = 200
}

variable "models" {
  description = "Models to serve, one systemd service each. ref is a Hugging Face repo, revision its commit sha, gpu the CUDA device index. Values are validated because they reach a shell on the VM."
  type = list(object({
    name     = string
    kind     = string
    ref      = string
    revision = string
    port     = number
    gpu      = number
  }))
  default = [
    { name = "kev-9b", kind = "kev", ref = "jaredpalmer/kev-9b", revision = "2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c", port = 8009, gpu = 0 },
    { name = "open-jev-9b", kind = "openjev", ref = "ZefanCai/Open-Jev-9B", revision = "47e966881e489511c0c7f5633a9e1960a676a551", port = 8791, gpu = 1 },
  ]
  validation {
    condition     = alltrue([for m in var.models : can(regex("^[a-z0-9][a-z0-9-]{0,40}$", m.name))])
    error_message = "model.name: lowercase letters, digits, hyphen; max 41 chars; no dots."
  }
  validation {
    condition     = alltrue([for m in var.models : contains(["kev", "openjev", "laya", "strands"], m.kind)])
    error_message = "model.kind must be kev, openjev, laya or strands."
  }
  validation {
    condition     = alltrue([for m in var.models : can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", m.ref))])
    error_message = "model.ref must be a Hugging Face owner/repo id."
  }
  validation {
    condition     = alltrue([for m in var.models : can(regex("^[0-9a-f]{40}$", m.revision))])
    error_message = "model.revision must be a 40-hex commit sha."
  }
  validation {
    condition     = alltrue([for m in var.models : m.port >= 1024 && m.port <= 65535 && m.gpu >= 0 && m.gpu <= 7])
    error_message = "model.port in 1024..65535, model.gpu in 0..7."
  }
}

variable "kev_repo_sha" {
  description = "Pinned commit of github.com/jaredpalmer/kev whose server is run on the VM."
  type        = string
  default     = "90990a5fac2995b9faa3190f7d437e84f2067768"
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.kev_repo_sha))
    error_message = "40-hex commit sha."
  }
}

variable "laya_version" {
  description = "Pinned PyPI release of the author's laya package that loads convaiinnovations/laya checkpoints."
  type        = string
  default     = "0.3.5"
  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.laya_version))
    error_message = "laya_version must be an exact x.y.z release."
  }
}

variable "strands_decider_version" {
  description = "Pinned PyPI release of strands-decider, whose create_app serves kind = \"strands\" models (StrandsAgents/strands-decider-2B-hobson-v19)."
  type        = string
  default     = "0.1.0"
  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.strands_decider_version))
    error_message = "strands_decider_version must be an exact x.y.z release."
  }
}

variable "openjev_repo_sha" {
  description = "Pinned commit of github.com/Zefan-Cai/Open-Jev whose server is run on the VM."
  type        = string
  default     = "ed45657bf726c3b77408942830e5578f99df904e"
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.openjev_repo_sha))
    error_message = "40-hex commit sha."
  }
}

variable "uv_version" {
  description = "Pinned uv release installed on the VM; the installer script is checksum-verified."
  type        = string
  default     = "0.6.11"
}

variable "uv_installer_sha256" {
  description = "sha256 of https://astral.sh/uv/<uv_version>/install.sh. Recompute when bumping uv_version."
  type        = string
  default     = "3ad71dec3bddbbe7f0d3b5bd1fe58290b593131528636ab1d407855a687f8f65"
}

variable "idle_shutdown_minutes" {
  description = "Power off after this many minutes with no GPU activity. 0 disables. First line of cost defence."
  type        = number
  default     = 60
}

variable "max_run_hours" {
  description = "Hard cap: the VM is stopped this many hours after it starts, whatever it is doing. Second line of cost defence; the pawoffice GPU incident was an unbounded retry times timeout."
  type        = number
  default     = 8
}

variable "direct_access_cidrs" {
  description = "CIDRs allowed to reach the model ports directly on the external IP (for `endpoints.resolve(mode=\"direct\")`). Empty keeps the ports closed and forces IAP tunnels."
  type        = list(string)
  default     = []
}

variable "attach_service_account" {
  description = "Create and attach a logging/metrics-only service account. The VM serves models without any credentials, so false is safe; it also avoids the IAM API when that API is unreachable."
  type        = bool
  default     = true
}
