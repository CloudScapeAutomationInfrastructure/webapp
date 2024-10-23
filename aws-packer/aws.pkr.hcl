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

source "amazon-ebs" "ubuntu-webapp" {
  region                      = var.region
  source_ami                  = var.source_ami
  instance_type               = var.instance_type
  ssh_username                = var.ssh_username
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
    source      = "install.sh" # Change to a specific file path
    destination = "/tmp/install.sh"
  }

  provisioner "file" {
    source      = "flask_setup.sh" # Change to the specific script file
    destination = "/tmp/flask_setup.sh"
  }

  provisioner "shell" {
    inline = [
      "chmod +x /tmp/install.sh",
      "chmod +x /tmp/flask_setup.sh",
      "/tmp/install.sh",    # Run install script
      "/tmp/flask_setup.sh" # Run flask setup script
    ]
  }

  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
  }
}
#end of file