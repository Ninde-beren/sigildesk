#!/usr/bin/env bash
# Machine virtuelle Lubuntu 26.04 proche de l'ASUS E402SA, pour valider ce
# qu'un conteneur ne montre pas : session LXQt, plein écran sous le gestionnaire
# de fenêtres, raccourci Ctrl+Alt+M, lxqt-leave, autostart, associations MIME.
#
#   scripts/vm-lubuntu.sh live    ISO   # session live : rien n'est conservé
#   scripts/vm-lubuntu.sh install ISO   # crée le disque et lance l'installateur
#   scripts/vm-lubuntu.sh run           # redémarre la VM installée
#
# 4 Go de RAM, 2 cœurs, écran 1368×768 (au plus près des 1366×768 de l'ASUS), son par PipeWire. Si build/vm/cle-usb
# existe (scripts/vm-cle-usb.py), il est branché comme une clé USB : dans la VM,
#   udisksctl mount -b /dev/sda1; bash /run/media/$USER/*/vm-installe.sh
# installe et lance SigilDesk. Le dépôt est aussi partagé en lecture seule (9p) :
#   sudo mkdir -p /mnt/sigildesk
#   sudo mount -t 9p -o trans=virtio,version=9p2000.L,ro sigildesk /mnt/sigildesk
#   cp -r /mnt/sigildesk ~/sigildesk-app && cd ~/sigildesk-app
#
# Limite : le processeur de l'hôte est bien plus rapide qu'un Celeron N3060.
# La VM ne dit rien des performances : mesurer sur l'ASUS (scripts/measure.py).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
vm_dir="${SIGILDESK_VM_DIR:-$here/build/vm}"
disk="$vm_dir/lubuntu-26.04.qcow2"
mode="${1:-}"
iso="${2:-}"

common=(
    -enable-kvm -machine q35 -cpu host -smp 2 -m 4096
    # VGA standard : la taille reste fixe quelle que soit la fenêtre (virtio-vga,
    # lui, suit la fenêtre et donnait du 5120×2160). 1368 et non 1366 : la VGA de
    # QEMU cisaille l'image si la largeur n'est pas un multiple de 8.
    -device VGA,xres=1368,yres=768,edid=on,vgamem_mb=32
    -display gtk,zoom-to-fit=on
    -netdev user,id=net0 -device virtio-net-pci,netdev=net0
    -device qemu-xhci -device usb-tablet
    -audiodev pipewire,id=son -device intel-hda -device hda-duplex,audiodev=son
    -virtfs "local,path=$here,mount_tag=sigildesk,security_model=none,readonly=on"
    -qmp "unix:$vm_dir/qmp.sock,server=on,wait=off"
    -name "Lubuntu 26.04 — essai SigilDesk"
)
mkdir -p "$vm_dir"

# Clé USB virtuelle (lecture seule) préparée par scripts/vm-cle-usb.py :
# SigilDesk, vm-installe.sh et les fichiers d'essai.
if [ -d "$vm_dir/cle-usb" ]; then
    common+=(-drive "if=none,id=cle,format=raw,readonly=on,file=fat:$vm_dir/cle-usb" -device usb-storage,drive=cle,removable=on)
fi

need_iso() {
    if [ -z "$iso" ] || [ ! -f "$iso" ]; then
        echo "Indiquez l'ISO Lubuntu 26.04, par exemple : $0 $mode ~/Downloads/lubuntu-26.04.1-desktop-amd64.iso" >&2
        exit 64
    fi
}

case "$mode" in
    live)
        need_iso
        exec qemu-system-x86_64 "${common[@]}" -cdrom "$iso" -boot d
        ;;
    install)
        need_iso
        mkdir -p "$vm_dir"
        if [ ! -f "$disk" ]; then
            qemu-img create -f qcow2 "$disk" 25G
        fi
        exec qemu-system-x86_64 "${common[@]}" -drive "file=$disk,if=virtio" -cdrom "$iso" -boot d
        ;;
    run)
        if [ ! -f "$disk" ]; then
            echo "Pas de VM installée ($disk). Lancez d'abord : $0 install ISO" >&2
            exit 1
        fi
        exec qemu-system-x86_64 "${common[@]}" -drive "file=$disk,if=virtio"
        ;;
    *)
        sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
        exit 64
        ;;
esac
