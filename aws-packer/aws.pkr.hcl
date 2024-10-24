packer {
  required_plugins {
    amazon = {
      version = ">= 1.0.0, < 2.0.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-2"
}

variable "source_ami" {
  type    = string
  default = "ami-0ea3c35c5c3284d82"
}

variable "vpc_id" {
  type    = string
  default = "vpc-0e5d46ba20ffe4e40"
}

variable "subnet_id" {
  type    = string
  default = "subnet-08e9f5466b55ae53c"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}
variable "envfile" {
  type    = string
  default = "./install.sh"
}


# New variable for the additional AWS account ID to share the AMI with
variable "additional_user" {
  type    = string
  default = "311141531170"
}

source "amazon-ebs" "ubuntu-webapp" {
  region                      = var.region
  source_ami                  = var.source_ami
  instance_type               = var.instance_type
  ssh_username                = var.ssh_username
  ami_users                   = [var.additional_user]
  ami_name                    = "webappServer-{{timestamp}}"
  ami_description             = "webappServer_vm-ubuntu-24-04-lts-${formatdate("YYYY_MM_DD_HH_MM", timestamp())}"
  vpc_id                      = var.vpc_id
  subnet_id                   = var.subnet_id
  associate_public_ip_address = true
  tags = {
    Name = "WebServer App AMI"
  }
}

build {
  sources = ["source.amazon-ebs.ubuntu-webapp"]
    provisioner "file" {
    source      = var.envfile  # The path passed from GitHub Actions
    destination = "/home/ubuntu/.env"  # Destination inside the instance/AMI
  }
  provisioner "file" {
    source      = "../app.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../config.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../conftest.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../models.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../routes.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../test_app.py"
    destination = "/tmp/"
  }
  provisioner "file" {
    source      = "../requirements.txt"
    destination = "/tmp/"
  }
   provisioner "file" {
    source      = var.envfile  # Path where the .env is created during GitHub Actions
    destination = "/home/ubuntu/.env"  # Target path inside the instance/AMI
  }
  provisioner "shell" {
    script = "install.sh"
  }

  provisioner "shell" {
    script = "flask_setup.sh"
  }

  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
  }

}
#eof
