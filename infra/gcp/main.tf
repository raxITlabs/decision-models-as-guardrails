# One GPU VM that serves open decision models on the System One contract.
# Reachable only through IAP SSH tunnels; no public ports.

resource "google_project_service" "apis" {
  for_each           = toset(["compute.googleapis.com", "iap.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "vm" {
  count        = var.attach_service_account ? 1 : 0
  account_id   = "gold-rails-serve"
  display_name = "Gold Rails model serving VM"
}

resource "google_project_iam_member" "vm_logs" {
  count   = var.attach_service_account ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm[0].email}"
}

resource "google_project_iam_member" "vm_metrics" {
  count   = var.attach_service_account ? 1 : 0
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.vm[0].email}"
}

# IAP's TCP forwarding range only. Nothing else reaches port 22.
resource "google_compute_firewall" "iap_ssh" {
  name    = "gold-rails-allow-iap-ssh"
  network = "default"
  allow {
    protocol = "tcp"
    # SSH plus the model ports: IAP TCP forwarding connects to the VM's NIC address, so the servers bind 0.0.0.0
    # and only this IAP range (and direct_access_cidrs, if set) can reach them.
    ports = concat(["22"], [for m in var.models : tostring(m.port)])
  }
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["gold-rails-serve"]
}

data "google_compute_image" "dlvm" {
  family  = "common-cu129-ubuntu-2404-nvidia-580"
  project = "deeplearning-platform-release"
}

resource "google_compute_instance" "serve" {
  name         = "gold-rails-serve"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["gold-rails-serve"]

  boot_disk {
    initialize_params {
      image = data.google_compute_image.dlvm.self_link
      size  = var.boot_disk_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    # Ephemeral external IP for outbound internet (installs, weights). Cheaper than a
    # NAT gateway for a VM that lives for hours. Inbound stays closed by the firewall:
    # only IAP's range reaches port 22, and the model ports are never opened.
    access_config {}
  }

  scheduling {
    provisioning_model          = var.spot ? "SPOT" : "STANDARD"
    preemptible                 = var.spot
    automatic_restart           = false
    on_host_maintenance         = "TERMINATE"
    instance_termination_action = "STOP"
    max_run_duration {
      seconds = var.max_run_hours * 3600
    }
  }

  # Logging and monitoring only. Weights come from Hugging Face over HTTPS, not from
  # GCS, and the VM runs third-party server code, so it gets no project-wide API access.
  # No credentials at all when attach_service_account is false: the VM only serves models and needs none.
  dynamic "service_account" {
    for_each = var.attach_service_account ? [1] : []
    content {
      email  = google_service_account.vm[0].email
      scopes = ["https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write"]
    }
  }

  metadata = {
    enable-oslogin        = "TRUE"
    models-json           = jsonencode(var.models)
    idle-shutdown-minutes = tostring(var.idle_shutdown_minutes)
    kev-repo-sha          = var.kev_repo_sha
    openjev-repo-sha      = var.openjev_repo_sha
    laya-version          = var.laya_version
    laya-server-py        = file("${path.module}/laya_server.py")
    strands-version       = var.strands_decider_version
    strands-server-py     = file("${path.module}/strands_server.py")
    uv-version            = var.uv_version
    uv-installer-sha256   = var.uv_installer_sha256
    # In the metadata map (not metadata_startup_script) so edits update in place instead of replacing the VM.
    startup-script = file("${path.module}/startup.sh")
  }

  depends_on = [google_project_service.apis]
}

# Optional: open the model ports to named CIDRs for direct access without tunnels.
resource "google_compute_firewall" "direct_models" {
  count   = length(var.direct_access_cidrs) > 0 ? 1 : 0
  name    = "gold-rails-allow-direct-models"
  network = "default"
  allow {
    protocol = "tcp"
    ports    = [for m in var.models : tostring(m.port)]
  }
  source_ranges = var.direct_access_cidrs
  target_tags   = ["gold-rails-serve"]
}
