# Samsung Galaxy M20 (m20lte / universal7904) Online Artifacts & Research Survey

**Date:** 2026-10-28  
**Target:** Samsung Galaxy M20 (`m20lte` / `m20ltedd`, SM-M205F/FN/G/M/N)  
**SoC:** Samsung Exynos 7904 (`S5E7904` / `universal7904`, variant of `universal7885`)  
**Context:** XNU/Darwin and iOS 16.5 bring-up on non-Apple ARM64 hardware (ported from `stormtroopxyz/y2sios`).

---

## 1. Executive Summary & Hardware Definition

The Samsung Galaxy M20 is a budget AArch64 smartphone released in January 2019. It is built on Samsung's Exynos 7904 SoC (an octa-core big.LITTLE design fabricated on 14nm FinFET), pairing 2x ARM Cortex-A73 performance cores with 6x ARM Cortex-A53 efficiency cores.

### 1.1 Key Hardware Specifications

| Component | Target (`m20lte`) | Reference (`y2s` / Exynos 990) | Port Impact |
|---|---|---|---|
| **SoC** | Exynos 7904 (`S5E7904`) | Exynos 990 (`S5E9830`) | Entire peripheral base map and clock tree differ. |
| **CPU Topology** | 2x Cortex-A73 @ 1.8-2.2 GHz + 6x Cortex-A53 @ 1.6-1.8 GHz | 2x M5 + 2x Cortex-A76 + 4x Cortex-A55 | Standard ARMv8.0-A; PSCI v0.2/v1.0 supported via EL3 secure monitor. |
| **Interrupt Controller** | ARM GICv2 (`0x12301000` GICD, `0x12302000` GICC) | ARM GICv3 (`0x10100000` GICD, `0x10140000` GICR) | Requires `GIC_V2=1` compile flag; legacy MMIO banked interface. |
| **DRAM** | 2 GB, 3 GB, or 4 GB LPDDR4x | 8 GB / 12 GB LPDDR5 | Window size must fit within 2 GB SKU (`~1.2 GB` usable after reserved firmware regions). |
| **Storage** | eMMC 5.1 (`dwmmc0` @ `0x13500000`) | UFS 3.0 / 3.1 (`ufs` @ `0x15700000`) | **Hard divergence**: eMMC uses Synopsys DesignWare MMC, not Samsung UFS HCI. |
| **Internal Partition Table** | GPT on eMMC (no dynamic `super` partition) | GPT + dynamic `super` on UFS | Port disk is the 38 MiB raw `recovery` partition. |
| **Display Panel** | 1080x2340 (19.5:9, Infinity-V TFT PLS LCD) | 1125x2436 Dynamic AMOLED | Fixed video-mode DSI panel; CPU-copy framebuffer required initially. |
| **Display Controller** | DECON-F (`0x14860000`) + DSIM (`0x14870000`) | DECON-F (`0x19050000`) + DSIM (`0x190C0000`) | Hardware DPU programming sequence differs; accelerated paths bypassed. |
| **GPU** | ARM Mali-G71 MP2 / Mali-T830 MP3 (`0x11500000`) | ARM Mali-G77 MP11 (`0x11000000`) | Midgard/Bifrost architecture; deferred to post-userland phase. |
| **PMIC / Charger** | Samsung S2MPU08 + S2MPB03 + S2MU004 | Shannon / Maxim PMIC | Battery status and power keys driven over I2C. |
| **Touchscreen** | Himax HX83112A over I2C (`0x13870000`, I2C4) | Synaptics / SEC TSP over SPI | Requires dedicated Himax I2C driver in userland/kernel. |
| **USB Controller** | Synopsys DWC3 USB 2.0/3.0 (`0x13600000`) | Synopsys DWC3 USB 3.1 | Driven via `EFI_USBFN_IO_PROTOCOL` in UEFI / loader. |

---

## 2. Survey of Online Repositories & Artifacts

### 2.1 Device Trees & AOSP Sources
* **LineageOS Official Wiki & Device Tree:**
  * Repo: `LineageOS/android_device_samsung_m20lte` (branch `lineage-18.1`)
  * Kernel Source: `LineageOS/android_kernel_samsung_universal7904`
  * Wiki Metadata: `https://wiki.lineageos.org/devices/m20lte/`
  * Insights: Contains exact partition layouts, board config (`BoardConfig.mk`), LCD density (`420 dpi`), eMMC mount options, and SELinux policies.
* **SamarV-121 AOSP & Vendor Trees:**
  * `SamarV-121/android_device_samsung_m20lte`
  * `SamarV-121/proprietary_vendor_samsung_m20lte`
  * `SamarV-121/android_kernel_samsung_universal7885` (FuseKernel)
  * Insights: SamarV-121 is the primary maintainer for universal7885/7904 custom ROMs. Includes camera, audio HAL, and sensor configuration tables.

### 2.2 Recovery Projects
* **OrangeFox Recovery Project:**
  * Repo: `OrangeFoxRecovery/device_samsung_m20lte` (branch `fox_9.0`)
  * Manifest: `txorav/orangefox_manifest`
  * Partition mapping confirms:
    * `/dev/block/platform/13500000.dwmmc0/by-name/BOOT` (Kernel/ramdisk slot: 32 MiB)
    * `/dev/block/platform/13500000.dwmmc0/by-name/RECOVERY` (Recovery partition: 38 MiB / `0x2600000`)
    * `/dev/block/platform/13500000.dwmmc0/by-name/SYSTEM` (System: 3.56 GB / 3565158400 bytes)
    * `/dev/block/platform/13500000.dwmmc0/by-name/USERDATA` (Data partition)
* **PitchBlack Recovery Project (PBRP):**
  * `PitchBlackRecoveryProject/android_device_samsung_m20lte-pbrp`

### 2.3 Kernel & Mainlining Artifacts
* **`txorav/pox-kernel-m20lte`:**
  * Production kernel tree based on Exynos 7904 Linux 4.4.
  * Contains crucial display documentation: `docs/m20lte-display.md`:
    * Panel: 1080x2340 60Hz PLS LCD, HWC2 compositor.
    * DECON: `0x14860000`, DSIM: `0x14870000`.
    * GPU: ARM Mali at `0x11500000`.
    * DRAM: 3 GB configuration, zRAM settings.
* **PostmarketOS / Mainline Linux:**
  * `device/downstream/linux-samsung-m20lte` in postmarketOS.
  * Work on `universal7885` mainline SoC support (DTSI files: `exynos7885.dtsi`, `exynos7904-m20lte_common.dtsi`).
* **KVM on m20lte:**
  * `raspiduino/m20lte-kvm`: Demonstrates virtualization / EL2 availability on unlocked bootloader.

### 2.4 UEFI & Mu-Silicium Repositories
* **`txorav/mu-silicium-m20lte`:**
  * Dedicated fork for Samsung Galaxy M20 UEFI.
  * Builds `m20ltePkg` using Mu-Silicium infrastructure:
    * `Platforms/Samsung/m20ltePkg/m20lte.dsc`
    * `Platforms/Samsung/m20ltePkg/DeviceBuild.py`
    * `Platforms/Samsung/m20ltePkg/Library/MemoryMapLib/MemoryMapLib.c`
    * Integrates `S5E7870Pkg/Library/PlatformMshcLib` for eMMC controller initialization.
* **`txorav/ios-greatlte`:**
  * Reference XNU port for Exynos 8895 (Samsung Galaxy Note 8).
  * Demonstrates GICv2 setup, secondary CPU bring-up via PSCI, and Mach-O kernel bootstrap.

---

## 3. Storage Architecture: eMMC vs UFS

The most significant divergence between `y2sios` and `m20lte` is the storage subsystem:

```mermaid
flowchart TD
    subgraph y2s (Exynos 990)
        UFS_DEV[Samsung UFS 3.0 / 3.1] --> UFS_HCI[UFS HCI @ 0x15700000]
        UFS_HCI --> UFS_DRV[redwood_ufs.c]
        UFS_DRV --> SUPER_PART[Dynamic Super Partition]
        SUPER_PART --> APFS_VOLS[System / Data APFS]
    end

    subgraph m20lte (Exynos 7904)
        EMMC_DEV[Samsung eMMC 5.1] --> DWM_CTRL[DesignWare MMC dwmmc0 @ 0x13500000]
        DWM_CTRL --> EFI_BIO[UEFI EFI_BLOCK_IO_PROTOCOL]
        EFI_BIO --> MSHC_DXE[MshcDxe + PlatformMshcLib]
        MSHC_DXE --> REC_PART[Raw 38 MiB Recovery Partition]
        REC_PART --> RAMDISK[In-Memory Ramdisk md0]
    end
```

### 3.1 Partition Layout of the 38 MiB Recovery Disk

In Bring-up Phase 1 (Layout A), the phone's 38 MiB raw recovery partition is sliced to host the entire port payload:

```
  0x0000000 +0x0400000 (4 MiB)   : Android boot.img (BootShim + UEFI FD 2 MiB + XNUP Payload 512 KB)
  0x0400000 +0x0800000 (8 MiB)   : Loader execution & panic log ring buffer
  0x0C00000 +0x1200000 (18 MiB)  : Mach-O XNU Kernel (koff=0xC00000, ksize=0x1200000)
  0x1E00000 +0x0400000 (4 MiB)   : Monolithic APFS root ramdisk (root.apfs / md0)
  0x2200000 +0x0400000 (4 MiB)   : Spare / scratch buffer
  0x2600000                       : End of 38 MiB partition
```

---

## 4. Boot Chain & Memory Map Constraints

### 4.1 Reserved Memory & Firmware Exclusion Zones

From `exynos7884-rmem.dtsi` and `MemoryMapLib.c`:
- `0x80000000` (1 page): Dynamic Secure
- `0x8F000000` - `0x8F200000` (2 MiB): UEFI Firmware Descriptor (`FD_BASE`)
- `0x8F100000` - `0x8F180000` (512 KB): XNUP payload inside the FD tail (`PAYLOAD_BASE`)
- `0xB8000000` (2 MiB): TIMA (TrustZone Integrity Measurement)
- `0xC0000000` (512 KB): Seclog
- `0xE0000000` (13 MiB): Secure Reserved
- `0xEC000000` (64 MiB): Display Framebuffer pool (`FB_BASE`)
- `0xF5400000` (8.8 MiB): Modem CP Interface
- `0xFDC00000` (32 MiB): CP Logging
- `0xFFC00000` (4 MiB): GNSS IF

### 4.2 Dynamic Window Selection

Because DRAM can be as small as 2 GiB on base M20 models, `choose_window()` dynamically queries UEFI `GetMemoryMap` to claim the largest available block of contiguous `EfiConventionalMemory`. 

To prevent memory clobbering:
1. `ensure_kernel_stage()` allocates the 24 MiB staging buffer *before* `choose_window()` scans the memory map, converting those pages to `EfiLoaderData`.
2. `choose_window()` claims the remaining largest continuous block via `BS->allocate_pages(AllocateAddress, EfiLoaderData, ...)`.
3. The kernel Mach-O segments are unpacked from `kernel_stage` into `win_base + slide` safely without self-overwrite.

---

## 5. Summary of Bring-up Status

1. **UEFI Package (`m20ltePkg`):** Configured with 1080x2340 panel dimensions, stride 1088, eMMC Mshc library bindings, and memory exclusions.
2. **XNU Loader (`loader.c`):** Updated with dynamic staging allocation, Mach-O segment validation, fastboot `hex_string()` formatting, and recovery log persistence.
3. **Display Driver (`MiniIOMobileFramebuffer.cpp`):** Base addresses for Exynos 7904 DECON/DSIM mapped (`0x14860000`/`0x14870000`); accelerated paths clamped to CPU-copy fallback.
4. **Userland APFS Root (`userland/build.sh`):** `M20_BRINGUP=1` builds a self-contained 4 MiB monolithic root with `/sbin/launchd` as `init`, running `etc/rc` and halting for log capture.
5. **Verification Tools:** `kernel/tools/layout_check.py` and `kernel/tools/m20-root-check.sh` fully validate the artifact layout and synthetic APFS tree on the host without hardware.
