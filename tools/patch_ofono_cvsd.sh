#!/bin/bash
# patch_ofono_cvsd.sh — força oFono a usar SÓ CVSD (desliga mSBC/wideband)
# Motivo: adapter Qualcomm USB (hci0 74:C6:3B:87:06:88) REJEITA eSCO/mSBC
#   com Status 0x0d (Connection Rejected due to Limited Resources).
#   Celular (moto g35) sempre pede eSCO apos negociar codec. Se oFono so
#   oferece CVSD, celular ainda pede eSCO mas pelo menos nao tenta mSBC.
#   (Nota: ainda falta resolver o controller aceitar eSCO com param CVSD —
#    ver MEMORY.md secao HFP.)
#
# Patch: funcao ofono_handsfree_audio_has_wideband @ vaddr 0x184dd4
#   original: 8b 05 a6 66 0a 00   (mov eax, [global wideband flag])
#   patch:    31 c0 90 90 90 90   (xor eax,eax ; nop*4) => return 0
#
# Uso: sudo bash tools/patch_ofono_cvsd.sh
# Reaplicar apos `apt upgrade` de ofono (binario eh sobreescrito).
set -e
OFONO=/usr/sbin/ofonod
OFF=0x184dd4
ORIG="8b05a6660a00"
PATCH="31c090909090"

echo "[1/4] Parando ofono..."
sudo systemctl stop ofono || true
sleep 1

echo "[2/4] Backup original (uma vez)..."
if [ ! -f "${OFONO}.orig" ]; then
  sudo cp "$OFONO" "${OFONO}.orig"
  echo "   backup: ${OFONO}.orig"
else
  echo "   backup ja existe"
fi

echo "[3/4] Aplicando patch em $OFF ..."
sudo python3 - "$OFONO" "$OFF" "$ORIG" "$PATCH" <<'PY'
import sys
f=open(sys.argv[1],'r+b')
off=int(sys.argv[2],16)
orig=bytes.fromhex(sys.argv[3])
patch=bytes.fromhex(sys.argv[4])
f.seek(off)
cur=f.read(6)
print("   atual :", cur.hex())
if cur == patch:
    print("   JA PATCHADO — nada a fazer")
elif cur == orig:
    f.seek(off); f.write(patch)
    f.seek(off); print("   patch  :", f.read(6).hex(), "OK")
else:
    print("   ! bytes inesperados, abortando (binario diferente?)", file=sys.stderr)
    sys.exit(1)
f.close()
PY

echo "[4/4] Subindo ofono..."
sudo systemctl start ofono
sleep 2
echo "ofono ativo: $(systemctl is-active ofono)"
echo "Pronto. oFono agora so negocia CVSD (has_wideband=0)."
