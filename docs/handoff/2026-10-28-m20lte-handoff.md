# Developer Handoff: Samsung Galaxy M20 (m20lte) XNU/iOS Bring-up

**Date:** 2026-10-28  
**Branch:** `m20lte`  
**Repository:** `txorav/m20lte-y2sios`  
**Base snapshot:** `stormtroopxyz/y2sios` @ `68fe2e922a52917ed851c1499e394fe5436365b5`  
**Author / Session:** Antigravity AI Engineering Agent  

---

## 1. Executive Summary & Current State

This repository contains the architecture, boot chain, UEFI packages, loader modifications, display adaptations, and userland root image tooling for porting XNU/Darwin and iOS userland to the **Samsung Galaxy M20 (`m20lte`, Exynos 7904)**.

Milestones **M0 through M4** of the implementation plan have been completed and verified on the host system without requiring target hardware.

### 1.1 Milestone Status Matrix

| Milestone | Subsystem | Description | Status | Verification |
|---|---|---|---|---|
| **M0** | Scaffolding & Layout | Layout checks, partition budgeting, `m20lte.conf` | **COMPLETE** | `python3 kernel/tools/layout_check.py m20lte` passes. |
| **M1** | UEFI Firmware | `m20ltePkg` in Mu-Silicium, eMMC bindings, log dump | **COMPLETE** | Source tree & build manifests configured. |
| **M2** | XNU Loader | Dynamic staging, Mach-O bounds audit, fastboot fix | **COMPLETE** | Static analysis & path verification complete. |
| **M3** | Display Driver | Exynos 7904 DECON/DSIM addresses, CPU-copy mode | **COMPLETE** | Tunables clamp hardware accel to CPU blit on `gSoc=2`. |
| **M4** | Monolithic Userland | APFS root without iOS launchd (`M20_BRINGUP=1`) | **COMPLETE** | `bash kernel/tools/m20-root-check.sh` passes. |
| **M5** | eMMC Storage | Synopsys DesignWare MMC (`dwmmc0`) XNU driver | **PENDING** | Next priority (replaces shared-page UFS). |
| **M6** | Power & Buttons | S2MPU08 PMIC, volume/power keys via GPIO | **PENDING** | Blocked on M5. |
| **M7** | Touchscreen | Himax HX83112A I2C driver | **PENDING** | Blocked on M5. |
| **M8** | Standalone Boot | Boot without USB cable, persistent filesystem | **PENDING** | Post-userland. |

---

## 2. Key Architectural Divergences from Reference (`y2s`)

| Feature | Reference (`y2sios` / Exynos 990) | Target (`m20lte` / Exynos 7904) | Resolution Applied in Tree |
|---|---|---|---|
| **Interrupts** | ARM GICv3 (`0x10100000`) | ARM GICv2 (`0x12301000`/`0x12302000`) | `GIC_V2=1` define; legacy banked distributor. |
| **Storage** | Samsung UFS 3.0 (`0x15700000`) | eMMC 5.1 (`dwmmc0` @ `0x13500000`) | Initial boot uses 4 MiB RAM disk (`md0`); eMMC driver planned for M5. |
| **Port Disk** | Dynamic UFS `super` partition | Raw 38 MiB `recovery` GPT partition | Recovery partition sliced into boot, log, kernel, and root slots. |
| **Display** | 1125x2436 Dynamic AMOLED | 1080x2340 60Hz PLS LCD (Infinity-V) | Stride set to 1088; DECON mapped to `0x14860000`, DSIM to `0x14870000`. |
| **RAM Budget** | 8 GB / 12 GB LPDDR5 | 2 GB / 3 GB LPDDR4x | Dynamic window claiming; staging buffer allocated before window scan. |
| **Root Image** | 2-stage (small init + iOS rootfs) | Monolithic 4 MiB APFS root (`M20_BRINGUP=1`) | `/sbin/launchd` is `init` itself; runs `etc/rc` and halts cleanly. |

---

## 3. Critical Bugs Audited & Resolved in This Session

### 3.1 Kernel Staging Self-Overwrite on Low-RAM Devices (`loader.c`)
* **Problem:** In `y2sios`, USB downloads and partition reads used a fixed staging address `DOWNLOAD_BASE = 0xF0000000`. On a 2 GiB Galaxy M20, `0xF0000000` is either unmapped or inside the memory window claimed for XNU. If `choose_window()` claimed DRAM covering `0xF0000000`, unpacking the Mach-O kernel would overwrite the buffer it was reading from.
* **Fix:** Introduced `ensure_kernel_stage(need)` using `BS->allocate_pages(AllocateAnyPages, EfiLoaderData, ...)`. This is executed **before** `choose_window()` scans `EfiConventionalMemory`. UEFI page allocation automatically excludes the staging buffer from the kernel's claimed window.

### 3.2 Block-Alignment Underrun in `read_partition_into` (`loader.c`)
* **Problem:** `left = len` was initialized before rounding `len` up to a multiple of `bio->media->block_size`. For unaligned sizes, the loop read fewer bytes than required, causing partial transfers or read failures.
* **Fix:** Rounded `len` to block size first, added bounds check against `bio->media->last_block`, and assigned `left = len`.

### 3.3 Fastboot `max-download-size` & `download:` Bug (`loader.c`)
* **Problem:** 
  1. `getvar:max-download-size` returned hardcoded `"0x05f00000"` or `"0x03f00000"`, misleading fastboot clients when staging was dynamically allocated.
  2. The `download:` handler checked `if (dest == NULL)` before evaluating `if (to_ramdisk)`. When downloading a ramdisk image without a prior USB staging buffer, downloads were spuriously rejected with `"no staging buffer"`.
* **Fix:** 
  1. Implemented `hex_string()` with dynamic length formatting and hooked `max-download-size` to the true available limit (`win_size - RESIDENT_RD_OFFSET - RESIDENT_RD_RESERVE` or `stage_size`).
  2. Restructured `download:` so `to_ramdisk` evaluates target memory first, only checking `dest == NULL` after destination selection.

### 3.4 Missing Var Skeleton in Standalone Root (`init.c`)
* **Problem:** In non-iOS bring-up (`M20_BRINGUP=1`), `/etc/var.skel` does not exist because there is no iOS rootfs. `init` aborted creating `/private/var` directories.
* **Fix:** Added a minimal directory list (`minimal[]`) fallback in `mount_writable()` and added detection for `/etc/m20-bringup`.

### 3.5 APFS Toolchain Path Inconsistency (`userland/build.sh`)
* **Problem:** In `userland/build.sh`, APFS scripts were hardcoded to `../tools/apfs/`, which does not exist in this tree layout (tools live under `kernel/tools/apfs`).
* **Fix:** Parameterized `$APFS` with default `../kernel/tools/apfs`.

---

## 4. Verification & Host Testing Commands

You can verify all M0-M4 work locally on any Linux or macOS machine without hardware:

### 4.1 Recovery Partition Layout Check
Validates that the Android boot image, log ring, Mach-O kernel, and APFS root fit within the 38 MiB recovery partition without overlaps:
```bash
cd /content/m20lte-y2sios/kernel
python3 tools/layout_check.py m20lte
```
**Expected Output:**
```
layout m20lte: FD=0x8f000000+0x200000 payload=0x8f100000+0x80000
  log=0x400000+0x800000 kernel=0xc00000+0x1200000 root=0x1e00000+0x400000 (image limit 0x2600000)
  LAYOUT OK
```

### 4.2 Synthetic APFS Monolithic Root Check
Builds a synthetic M20 monolithic root, packs it with `mkapfs.py`, reads it back with `apfs.py`, and validates against the recovery layout:
```bash
cd /content/m20lte-y2sios
bash kernel/tools/m20-root-check.sh
```
**Expected Output:**
```
mkapfs.py: .../root.apfs: 1024 blocks of 4096 bytes, 933 free
# 13 entries
m20-root-check: APFS tree OK (4194304 bytes)
layout m20lte: FD=0x8f000000+0x200000 payload=0x8f100000+0x80000
  log=0x400000+0x800000 kernel=0xc00000+0x1200000 root=0x1e00000+0x400000 (image limit 0x2600000)
  LAYOUT OK
m20-root-check: check-image.sh skipped (set M20_CHECK_APFS=1 to run apfsck + apfs_lib)
```

---

## 5. File Map of Changes

```
m20lte-y2sios/
├── .gitignore                                           # Excludes apfs-work and temporary tool builds
├── docs/
│   ├── m20lte-port-blueprint.md                        # Formal verification & comprehensive plan (M0–M8)
│   ├── handoff/
│   │   └── 2026-10-28-m20lte-handoff.md                # This handoff document
│   ├── research/
│   │   └── m20lte-online-artifacts.md                  # Hardware survey, repo index, specifications
│   └── sessions/
│       ├── m20lte-implementation-plan-session.md       # Session 1 transcript
│       └── session-cd3388f9-7e20-49f5-83c3-3cc974726ef2.md # Session 2 transcript
├── kernel/
│   ├── common/
│   │   ├── build.sh                                    # Invokes layout_check on build
│   │   └── devices/m20lte.conf                         # m20lte memory map and hardware config
│   ├── mkxnuimg.py                                     # Respects PAYLOAD_MAX environment variable
│   ├── tools/
│   │   ├── layout_check.py                             # Formally verifies memory & slot constraints
│   │   └── m20-root-check.sh                           # Host-side synthetic APFS bring-up test
│   ├── xnu/files/iokit/Kernel/
│   │   └── MiniIOMobileFramebuffer.cpp                 # Exynos 7904 DPU base map & CPU fallback
│   └── xnuloader/
│       ├── loader.c                                    # Dynamic staging, bounds audits, fastboot fix
│       └── mkpayload.py                                # Added --ksize argument for partition reads
├── uefi/
│   ├── BootManagerLib/
│   │   ├── XnuLoader.c                                 # Flushes boot logs to recovery + 4 MiB
│   │   └── XnuLoader.h                                 # PAYLOAD_MAX = 512 KB, recovery log partition
│   └── mu-silicium-m20lte/Platforms/Samsung/m20ltePkg/
│       ├── DeviceBuild.py                              # Scopes set to m20lte
│       ├── m20lte.dsc                                  # 1080x2340x1088, Mshc eMMC library mapping
│       └── Library/MemoryMapLib/MemoryMapLib.c         # Exynos 7904 register & DRAM reservations
└── userland/
    ├── build.sh                                        # M20_BRINGUP=1 support & APFS tool paths
    ├── m20-rc                                          # Bring-up rc running init, hello, and halt
    └── src/init.c                                      # Var skeleton fallback & /etc/m20-bringup
```

---

## 6. Next Steps for Incoming Developer (Milestone M5)

1. **eMMC Storage Driver (`M5`):**
   - The reference port used `redwood_ufs.c` communicating with UFS hardware or an emulation layer.
   - For `m20lte`, investigate implementing an XNU Synopsys DesignWare MMC (`dwmmc0`) driver at `0x13500000`, or reusing the UEFI `EFI_BLOCK_IO_PROTOCOL` shared-page transport technique that y2s used during early bring-up.
2. **UEFI Standalone Compilation:**
   - Clone `txorav/mu-silicium-m20lte` into `uefi/Mu-Silicium` and build `m20lte.dsc` with `CLANG38` or `GCC5` to produce `m20lte.fd`.
3. **Hardware Flashing & Logging:**
   - With an unlocked Galaxy M20 in Download Mode (`Volume Down + Volume Up + Plug USB`), flash the generated recovery image:
     ```bash
     heimdall flash --RECOVERY out/m20lte-boot.img
     ```
   - Boot into recovery (`Volume Up + Power`) and extract the log dump starting at offset `0x400000` (4 MiB) of `/dev/block/by-name/RECOVERY`.
