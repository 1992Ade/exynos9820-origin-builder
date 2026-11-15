# Exynos 9820 Kernel Builder with OriginSU

[![Build](https://img.shields.io/badge/build-GitHub%20Actions-blue?logo=github-actions&logoColor=white)](https://github.com/1992Ade/exynos9820-origin-builder/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/1992Ade/exynos9820-origin-builder?label=latest&logo=github)](https://github.com/1992Ade/exynos9820-origin-builder/releases/latest)

> **Your warranty is now void.** Flashing a custom kernel can brick your device. You are responsible for what you flash. Always keep a backup of your stock `boot` (and `vbmeta`) partitions.

## 📱 About This Repository

This repository automates the compilation of a custom **Linux 4.14** kernel for the **Samsung Galaxy S10 / Note10 / F62** family (**Exynos 9820 / 9825**). It is built from **[LeDrew2017's FreeRunner kernel source](https://github.com/LeDrew2017/android_kernel_samsung_exynos9820)** — the kernel behind **[FreeRunnerKernel](https://github.com/LeDrew2017/FreeRunnerKernel)**.

The upstream kernel ships with **KernelSU-Next**. This builder **replaces it with [OriginSU](https://github.com/samakshkambxj/OriginSU)** and adds **SuSFS**, **Baseband Guard**, **NoMount** and **Droidspaces** (see [Included features](#-included-features)). Each build is packaged as a recovery-flashable `.zip` (TWRP) with LeDrew's AnyKernel, **one per device**.

**Fully automated:** a GitHub Actions workflow checks every week (Sunday) for a new OriginSU release and, when one is out **with its manager APK**, rebuilds every device and publishes a release automatically.

---

## 💙 Prefer the original? Use LeDrew2017's FreeRunnerKernel

This project is **only an OriginSU rebuild**. All the real kernel work is **[LeDrew2017](https://github.com/LeDrew2017)'s**. If you'd rather run the original kernel with its own root solution (**KernelSU-Next / SukiSU**), get it directly from the developer — it is the reference build and is actively maintained:

- **Kernel source:** [LeDrew2017/android_kernel_samsung_exynos9820](https://github.com/LeDrew2017/android_kernel_samsung_exynos9820)
- **Build scripts:** [LeDrew2017/FreeRunnerKernel](https://github.com/LeDrew2017/FreeRunnerKernel)
- **A ROM that ships it (Galaxy S10+):** [Project Infinity-X — beyond2lte](https://projectinfinity-x.com/downloads/beyond2lte)

Please support the original developer first. 🙏

---

## 🧩 Included Features

On top of OriginSU, every build enables:

| Feature | Upstream | What it does | Kernel config |
|---|---|---|---|
| **SuSFS** | [simonpunk](https://gitlab.com/simonpunk/susfs4ksu) (4.14 patch by [JackA1ltman](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)) | Hides root/mounts from detection (`susfs` hook mode) | `CONFIG_KSU_SUSFS_*` |
| **Baseband Guard** | [vc-teahouse](https://github.com/vc-teahouse/Baseband-guard) | LSM that blocks writes to the modem/baseband partitions | `CONFIG_BBG=y` |
| **NoMount** | [maxsteeel](https://github.com/maxsteeel/nomount) | Prevents unwanted mounts used for root detection | `CONFIG_NOMOUNT=y` |
| **Droidspaces** | [ravindu644](https://github.com/ravindu644/Droidspaces-OSS) | Namespace/cgroup isolation to run isolated Android/Linux spaces | `CONFIG_NAMESPACES`, `CONFIG_USER_NS`, cgroups, netfilter… |

> On the Exynos 9820 defconfig, `CONFIG_MEMCG`, `CONFIG_CFS_BANDWIDTH` and `CONFIG_CGROUP_PIDS` are already enabled, so Droidspaces gets the **full** feature set here (memory, CPU and pids limits all available) — the builder just adds `CONFIG_USER_NS`. If you use it with a systemd-based Linux space, mask the `NetworkManager` and `wpa_supplicant` services inside it (as noted upstream).

---

## ✅ Supported Devices

LeDrew2017's kernel supports the whole Exynos 9820/9825 line-up. This builder produces one zip per device — **flash only the one matching your codename**:

| Device | Codename | Model | Status |
|---|---|---|---|
| Galaxy S10+ | `beyond2lte` | SM-G975F | ✅ **Tested by the maintainer** |
| Galaxy S10e | `beyond0lte` | SM-G970F | 🧪 Please test |
| Galaxy S10 | `beyond1lte` | SM-G973F | 🧪 Please test |
| Galaxy S10 5G | `beyondx` | SM-G977B | 🧪 Please test |
| Galaxy Note10 | `d1` | SM-N970F | 🧪 Please test |
| Galaxy Note10 5G | `d1x` | SM-N971 | 🧪 Please test |
| Galaxy Note10+ | `d2s` | SM-N975F | 🧪 Please test |
| Galaxy Note10+ 5G | `d2x` | SM-N976B | 🧪 Please test |
| Galaxy F62 | `f62` | SM-E625F | 🧪 Please test |

> ### 🧪 Community rebuild
> **Galaxy S10+ (`beyond2lte`) is tested and confirmed working.** The other devices are built automatically from the same sources but **not yet verified on real hardware**. Back up your stock `boot`/`vbmeta` first, and if a device doesn't boot, re-run the workflow with **`hook_mode = manual`** (root only, no SuSFS). Please open an issue reporting which devices boot.

**Requirement:** a ROM that runs the LeDrew2017 Exynos 9820 4.14 kernel (e.g. Project Infinity-X and other AOSP-based ROMs for these devices). Stock One UI is **not** supported.

---

## 📦 Which zip should I download?

Each release ships **one zip per device**, named:

```
exynos9820-<codename>-OriginSU-<version>-<hook>-<date>.zip
```

- **`-susfs-`** — SuSFS inline hook: root + SuSFS hiding (**recommended**).
- **`-manual-`** — manual hook only, no SuSFS: fallback if the SuSFS build doesn't boot.

A SHA-256 sum and the full kernel `.config` of each device are attached to the release.

---

## 🔧 Installation

1. Back up your stock `boot` and `vbmeta` partitions.
2. Download the zip **matching your device codename** from the [latest release](https://github.com/1992Ade/exynos9820-origin-builder/releases/latest).
3. Flash it in TWRP (or `adb sideload <file>.zip`).
4. Reboot, then install the **OriginSU manager** APK from the OriginSU release linked in the notes (same version as the kernel).

> **Updating the ROM?** An OTA replaces `boot`, so re-flash the zip after each ROM update.

### ↩️ Restore the stock kernel

```sh
su -c rm -rf /data/adb/*        # remove root data first
adb reboot bootloader
fastboot flash boot stock_boot.img
fastboot reboot
```

---

## ⚙️ How the Build Works

The workflow lives in [`.github/workflows/build.yml`](.github/workflows/build.yml) and runs three jobs:

```
check  ──►  build (matrix: 9 devices)  ──►  release
```

1. **check** — reads the latest stable OriginSU release, requires its **manager APK**, and pins JackA1ltman's SuSFS patch commit for the run. Builds only if there's a new `originsu-<tag>`.
2. **build** (one job per device, `fail-fast: false`)
   - Clones the chosen `android_kernel_samsung_exynos9820` branch (default `testing-fourteen-v3.0`, the FreeRunner branch that already ships SuSFS + KernelSU-Next) and downloads **Neutron Clang**. On that branch the SuSFS patch and hook scripts are skipped — the tree's own SuSFS is used and only the root solution is swapped to OriginSU. A clean branch (e.g. `testing-fifteen`) is patched with SuSFS instead.
   - Generates the config from `exynos9820-<device>_defconfig`.
   - **Replaces KernelSU-Next with OriginSU** (`rm -rf KernelSU drivers/kernelsu`, then OriginSU's `setup.sh` + small 4.14 compat fixes).
   - Adds **SuSFS** (JackA1ltman 4.14 patch + inline hooks; skipped if the branch already ships SuSFS) or, in `manual` mode, the manual hooks only.
   - Enables the **extra features** (Baseband Guard, NoMount, Droidspaces).
   - Compiles `Image` and packages it with LeDrew's AnyKernel, locked to that device.
3. **release** — publishes `originsu-<tag>` with every device zip, their SHA-256 sums, configs and a per-device table.

### Manual run options

| Input | Default | Description |
|---|---|---|
| `originsu_ref` | *(latest release)* | OriginSU tag to build |
| `kernel_branch` | `testing-fourteen-v3.0` | Branch of `android_kernel_samsung_exynos9820`. The `fourteen` branches already ship SuSFS (recommended, what FreeRunner uses); a clean branch like `testing-fifteen` gets SuSFS patched in |
| `hook_mode` | `susfs` | `susfs` = root + SuSFS; `manual` = root only (fallback) |
| `kpm` | `false` | Enable `CONFIG_KPM` |
| `publish` | `true` | Publish a GitHub Release |

> Scheduled workflows are disabled by GitHub after **60 days without repo activity** — re-enable in the Actions tab or push a commit if auto-releases stop.

---

## 🙏 Credits & Acknowledgments

* **[LeDrew2017](https://github.com/LeDrew2017)** — For the **FreeRunner** Exynos 9820 kernel source, device support and AnyKernel. **This project is just a rebuild of their work.**
* **[OriginSU](https://github.com/samakshkambxj/OriginSU)** — For the kernel-based root solution used here.
* **[KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next)** — The root solution the original FreeRunner kernel ships with.
* **[simonpunk](https://gitlab.com/simonpunk/susfs4ksu)** — For SuSFS.
* **[JackA1ltman](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)** — For the 4.14 SuSFS patch and non-GKI hook scripts.
* **[vc-teahouse](https://github.com/vc-teahouse/Baseband-guard)** — For Baseband Guard.
* **[maxsteeel](https://github.com/maxsteeel/nomount)** — For NoMount.
* **[ravindu644](https://github.com/ravindu644/Droidspaces-OSS)** — For Droidspaces.
* **[Neutron Toolchains](https://github.com/Neutron-Toolchains)** — For the Clang toolchain.
* **[tiann/KernelSU](https://github.com/tiann/KernelSU)** — The project OriginSU is built upon.

## 📄 License

Kernel sources are licensed under **GPL-2.0**. See each upstream project for its own license.
