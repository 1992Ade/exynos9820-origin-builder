# Exynos 9820 Kernel Builder with OriginSU

[![Build](https://img.shields.io/badge/build-GitHub%20Actions-blue?logo=github-actions&logoColor=white)](https://github.com/1992Ade/exynos9820-origin-builder/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/1992Ade/exynos9820-origin-builder?label=latest&logo=github)](https://github.com/1992Ade/exynos9820-origin-builder/releases/latest)

> [!IMPORTANT]
> **The FreeRunner developer, [LeDrew2017](https://github.com/LeDrew2017), is taking this project over — and OriginSU `v4.3.0` stays the recommended root for this kernel in the meantime.**
> OriginSU has been renamed and rebuilt as **[KazeSU](https://github.com/KazeSU/KazeSU)**, so `v4.3.0` is the final OriginSU release and this builder is frozen on it. KazeSU targets modern (GKI 5.10+) kernels and **does not build on this Linux 4.14 kernel** (its SELinux code needs the 5.10+ layout), while OriginSU `v4.3.0` supports it fully (non-GKI hooks, SuSFS, built-in module mounting). **4.14 is also the newest kernel available for Exynos 9820**: Samsung never moved these devices to a newer kernel, and there is no mainline port.
> - **FreeRunner releases:** [LeDrew2017/FreeRunnerKernel](https://github.com/LeDrew2017/FreeRunnerKernel/releases)
> - **Kernel source:** [Project-Matrixx-New/android_kernel_samsung_exynos9820](https://github.com/Project-Matrixx-New/android_kernel_samsung_exynos9820)
>
> The OriginSU `v4.3.0` manager APK is attached to each release here (also on the KazeSU repository: [tag `v4.3.0`, release "legacy-v4.3.0"](https://github.com/KazeSU/KazeSU/releases/tag/v4.3.0)). Note that KazeSU `v1.0.0` works with this kernel too but new root hiding method is not implemented.

> **Your warranty is now void.** Flashing a custom kernel can brick your device. You are responsible for what you flash. Always keep a backup of your stock `boot` (and `vbmeta`) partitions.

## 📱 About This Repository

This repository automates the compilation of a custom **Linux 4.14** kernel for the **Samsung Galaxy S10 / Note10 / F62** family (**Exynos 9820 / 9825**). It is built from the **real FreeRunner kernel source, [Project-Matrixx-New/android_kernel_samsung_exynos9820](https://github.com/Project-Matrixx-New/android_kernel_samsung_exynos9820)** (branch `lineage-24.0`, FreeRunner v3.9) — the source that **[LeDrew2017's FreeRunnerKernel](https://github.com/LeDrew2017/FreeRunnerKernel)** releases are built from.

> `LeDrew2017/android_kernel_samsung_exynos9820`, used by earlier versions of this builder, is a December 2024 snapshot of hiratazx's Yuki v3.0 tree — **not** FreeRunner. Its kernels did not boot on current ROMs.

The upstream kernel ships with **KernelSU-Next**. This builder **replaces it with [OriginSU v4.3.0](https://github.com/KazeSU/KazeSU/releases/tag/v4.3.0)**, upgrades **SuSFS to v2.4.0** (FreeRunner ships v2.3.0), enables **TCP BBR + fq**, adds a couple of [optimizations](#-optimizations) and can add **Baseband Guard**, **NoMount** and **Droidspaces** (see [Included features](#-included-features)). Each build is packaged as a recovery-flashable `.zip` (TWRP) with LeDrew's AnyKernel, **one per device**, and the matching **OriginSU manager APK** is attached to each release.


**Manual builds only:** OriginSU will not get new releases, so there is no weekly check. Running the workflow by hand rebuilds OriginSU `v4.3.0` on the latest FreeRunner source.

---

## 💙 Use LeDrew2017's FreeRunnerKernel

This project is **only an OriginSU rebuild**. All the real kernel work is **[LeDrew2017](https://github.com/LeDrew2017)'s**, and he is taking this project over. Get the kernel directly from the developer — it is the reference build and it is actively maintained:

- **Kernel source:** [Project-Matrixx-New/android_kernel_samsung_exynos9820](https://github.com/Project-Matrixx-New/android_kernel_samsung_exynos9820)
- **Releases & build scripts:** [LeDrew2017/FreeRunnerKernel](https://github.com/LeDrew2017/FreeRunnerKernel/releases)
- **A ROM that ships it (Galaxy S10+):** [Project Infinity-X — beyond2lte](https://projectinfinity-x.com/downloads/beyond2lte)

Please support the original developer first. 🙏

### Versions at a glance

| | FreeRunner (original) | This builder |
|---|---|---|
| **Root** | KernelSU-Next / SukiSU | **OriginSU** `v4.3.0` (final) — KazeSU does not build on 4.14 |
| **SuSFS** | `v2.3.0` (in-tree) | **`v2.4.0`** (upgraded; `v2.3.0` in-tree still selectable) |
| **TCP congestion control** | BIC (default), CUBIC, Westwood, HTCP | **BBR (default)** + the same |
| **Default qdisc** | pfifo_fast (`fq` built but unused) | **`fq`** |
| **ZRAM algorithms** | lz4 (default) | lz4 (default) + **zstd** |
| **Tethering TTL/HL** | IPv4 `TTL` target | IPv4 `TTL` + **IPv6 `HL`** target |
| **Kernel base** | `lineage-24.0` (v3.9) | same |
| **Toolchain** | clang 21, `make LLVM=1` | LLVM 21.1.8, `make LLVM=1` |
| **Extra features** | — | **Baseband Guard · NoMount · Droidspaces** (optional) |
| **Kernel** | Linux 4.14 (Exynos 9820/9825) | same |

The point of this rebuild was **OriginSU** (+ the optional extra features). For everything else, and for every future update, use FreeRunner directly.

---

## 🧩 Included Features

Always included on top of OriginSU: **SuSFS**, **TCP BBR + fq** and the [optimizations](#-optimizations). Optional (`extra_features` input): Baseband Guard, NoMount, Droidspaces.

| Feature | Upstream | What it does | Kernel config |
|---|---|---|---|
| **SuSFS `v2.4.0`** | [simonpunk](https://gitlab.com/simonpunk/susfs4ksu), 4.14 port by [JackA1ltman](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | Root/mount hiding (`susfs` hook mode). Replaces FreeRunner's in-tree v2.3.0 (`susfs_version = intree` to keep it) | `CONFIG_KSU_SUSFS_*` |
| **TCP BBR + fq** | Google (upstream Linux) | BBR built in and **default** TCP congestion control (FreeRunner: BIC), on the **`fq` qdisc** (see [TCP BBR](#-tcp-bbr)). Mostly helps uploads, video calls and hotspot. Back to CUBIC: `sysctl -w net.ipv4.tcp_congestion_control=cubic` | `CONFIG_DEFAULT_BBR=y`, `CONFIG_DEFAULT_FQ=y` |
| **Baseband Guard** | [vc-teahouse](https://github.com/vc-teahouse/Baseband-guard) | LSM that blocks writes to the modem/baseband partitions | `CONFIG_BBG=y` |
| **NoMount** | [maxsteeel](https://github.com/maxsteeel/nomount) | Mounts modules without real mounts (VFS path redirection, nothing in `/proc/mounts`) — driven by OriginSU's *OriginMount* screen, see [Modules](#-modules) | `CONFIG_NOMOUNT=y` |
| **Droidspaces** | [ravindu644](https://github.com/ravindu644/Droidspaces-OSS) | Namespace/cgroup isolation to run isolated Android/Linux spaces | `CONFIG_NAMESPACES`, `CONFIG_USER_NS`, cgroups, netfilter… |

> On the Exynos 9820 defconfig, `CONFIG_MEMCG`, `CONFIG_CFS_BANDWIDTH` and `CONFIG_CGROUP_PIDS` are already enabled, so Droidspaces gets the **full** feature set here (memory, CPU and pids limits all available) — the builder just adds `CONFIG_USER_NS`. If you use it with a systemd-based Linux space, mask the `NetworkManager` and `wpa_supplicant` services inside it (as noted upstream).

### 🌐 TCP BBR

FreeRunner's defconfig does not build BBR (default: BIC) and, although the `fq` qdisc is built, the default qdisc stays `pfifo_fast`. This builder makes **BBR the default congestion control** and **`fq` the default qdisc** (the option already exists in the tree, only the config is changed). On 4.14, BBR can pace by itself, but with `fq` the qdisc applies the rate BBR computes and TCP skips its own per-connection pacing timer — cheaper on the CPU and more precise. The build fails if the final `.config` does not have `CONFIG_DEFAULT_TCP_CONG="bbr"` and `CONFIG_DEFAULT_NET_SCH="fq"`.

Check on the phone (root shell):

```sh
cat /proc/sys/net/ipv4/tcp_congestion_control   # bbr
cat /proc/sys/net/core/default_qdisc            # fq
```

### ⚡ Optimizations

FreeRunner is already well tuned: power-efficient workqueues, `vm.swappiness` up to 200, IPv4 `TTL` target, WireGuard, Simple LMK, an updated LZ4 with arm64 assembly decompression, Cortex-A55 code tuning and Samsung's EMS scheduler are all in the tree. This builder only adds what is missing (low risk; the build fails if they are not in the final `.config`):

| Change | Effect | How to use / check |
|---|---|---|
| `CONFIG_CRYPTO_ZSTD=y` | zstd becomes available for ZRAM (better compression than lz4, a bit more CPU). **lz4 stays the default** | `cat /sys/block/zram0/comp_algorithm` lists `zstd` |
| `CONFIG_IP6_NF_TARGET_HL=y` | IPv6 counterpart of the `TTL` target, e.g. to hide tethering from the carrier | `ip6tables -t mangle -A POSTROUTING -j HL --hl-set 64` |

Not included on purpose: ThinLTO (FreeRunner keeps it off; it can rename internal symbols that root/hiding code looks up at boot, for a small gain) and MGLRU (too large to backport to 4.14).

---

## ✅ Supported Devices

LeDrew2017's kernel supports the whole Exynos 9820/9825 line-up. This builder produces one zip per device — **flash only the one matching your codename**:

| Device | Codename | Model | Status |
|---|---|---|---|
| Galaxy S10+ | `beyond2lte` | SM-G975F | ✅ **Tested**: boots (v3.9, OriginSU + SuSFS v2.4.0 + BBR + extras) |
| Galaxy S10e | `beyond0lte` | SM-G970F | 🧪 Untested |
| Galaxy S10 | `beyond1lte` | SM-G973F | 🧪 Untested |
| Galaxy S10 5G | `beyondx` | SM-G977B | 🧪 Untested |
| Galaxy Note10 | `d1` | SM-N970F | 🧪 Untested |
| Galaxy Note10 5G | `d1x` | SM-N971 | 🧪 Untested |
| Galaxy Note10+ | `d2s` | SM-N975F | 🧪 Untested |
| Galaxy Note10+ 5G | `d2x` | SM-N976B | 🧪 Untested |
| Galaxy F62 | `f62` | SM-E625F | 🧪 Untested |

> ### 🧪 Community rebuild
> **Galaxy S10+ (`beyond2lte`) is tested and boots** on FreeRunner v3.9 with OriginSU + SuSFS v2.4.0 + BBR + extras (Project Infinity-X). If a build doesn't boot on your device, try `susfs_version = intree` (FreeRunner's SuSFS v2.3.0). The other devices are built from the same source but were never verified. If a problem comes from the kernel itself rather than from OriginSU, check [FreeRunner's own builds](https://github.com/LeDrew2017/FreeRunnerKernel/releases) first. Test in this order on one device: **1)** `root = ksunext` (FreeRunner as-is: must boot, validates the CI) → **2)** `root = originsu`, `hook_mode = manual` → **3)** `hook_mode = susfs` → **4)** `extra_features = true`. The first step that bootloops tells you where the problem is. Back up your stock `boot` first.

### 🧬 ROM compatibility

This is a **LineageOS kernel**: the FreeRunner source is the LineageOS kernel for the Exynos 9820 devices (default branch `lineage-24.0`, i.e. the LineageOS 24 / Android 17 device tree), with FreeRunner's tweaks on top.

- ✅ **LineageOS and LineageOS-based ROMs** for these devices — tested on **Project Infinity-X** (S10+).
- ⚠️ ROMs on an older LineageOS base (e.g. 23.x / Android 16) should also work, but are untested: if one bootloops, rebuild with `kernel_branch = ksunext-qpr2` (FreeRunner v3.8-R2, Android 16 QPR2).
- ❌ **Stock One UI and One UI-based ROMs are not supported** (different kernel and device tree).

---

## 📦 Which zip should I download?

Each release ships **one zip per device**, named:

```
exynos9820-<codename>-OriginSU-<version>-<hook>-<date>.zip
```

- **`-susfs-v2.4.0`** — SuSFS inline hook: root + SuSFS hiding (**recommended**). `-susfs-v2.3.0` = FreeRunner's in-tree SuSFS.
- **`-manual-`** — manual hook only, no SuSFS: fallback if the SuSFS build doesn't boot.
- **`-KSUNext-control-`** — FreeRunner unchanged (KernelSU-Next), only to validate the build chain.
- **`-extras`** suffix — Baseband Guard + NoMount + Droidspaces included.

A SHA-256 sum and the full kernel `.config` of each device are attached to the release.

---

## 🔧 Installation

0. **Coming from Magisk, APatch, KernelSU-Next or SukiSU?** Read [this warning](#️-coming-from-another-root-solution) first.
1. Back up your stock `boot` and `vbmeta` partitions.
2. Download the zip **matching your device codename** from the [latest release](https://github.com/1992Ade/exynos9820-origin-builder/releases/latest).
3. Flash it in TWRP (or `adb sideload <file>.zip`).
4. Reboot, then install the **OriginSU manager** APK attached to the same release (`OriginSU_v4.3.0_…-arm64-v8a-release.apk`, also on the [legacy-v4.3.0 page](https://github.com/KazeSU/KazeSU/releases/tag/v4.3.0)). It must match the kernel: do **not** install the KazeSU v1.x manager with this kernel.
5. **Pick a module mount mode** in the manager's **OriginMount** screen — otherwise modules that change `/system` are not mounted (see [Modules](#-modules)).

> **Updating the ROM?** An OTA replaces `boot`, so re-flash the zip after each ROM update.

### 🧱 Modules

OriginSU mounts modules itself. Choose how in the manager's **OriginMount** screen (the choice applies from the next boot):

| Mode | What it does |
|---|---|
| `auto` (default) | Uses a metamodule if one is installed, otherwise Magic Mount if you enabled it, otherwise **no mounting** |
| `nomount` | Uses the **NoMount** driver built into the kernel (`-extras` zips only): module files are injected without real mounts, so nothing shows in `/proc/mounts` |
| `builtin` | OriginSU's built-in Magic Mount |
| `metamodule` | Delegates to an installed metamodule (e.g. meta-overlayfs) |
| `off` | No module mounting (scripts, `sepolicy.rule` and `system.prop` still work) |

With an `-extras` zip, NoMount is already in the kernel and OriginSU talks to it directly: **do not install the separate NoMount module zip** on top. If your modules are installed but their files don't show up, you are probably in `auto` mode with nothing to mount them: pick a mode.

### ⚠️ Coming from another root solution?

If you previously used **Magisk, APatch, KernelSU-Next (FreeRunner's default), KernelSU or SukiSU**, your old modules are still in `/data/adb/modules` and will be loaded by OriginSU.

OriginSU ships its **own Zygisk (OriginZygisk)**. Old modules — especially another Zygisk implementation (ReZygisk, NeoZygisk, Zygisk Next) or Zygisk-based modules such as LSPosed — can conflict with it. The typical symptom is a phone that **boots fine but has no Wi-Fi, no mobile network and/or no camera**.

**Fix: uninstall all modules, then reinstall them one by one.** From a PC:

```sh
adb shell
su
for m in /data/adb/modules/*/; do touch "$m/remove"; done
rm -rf /data/adb/modules_update/*
reboot
```

Each module's `uninstall.sh` runs on the next boot. If some folders remain afterwards:

```sh
adb shell
su
rm -rf /data/adb/modules/*
reboot
```

Then reinstall your modules **one at a time**, checking Wi-Fi, network and camera after each reboot. Use **only one Zygisk** (keep OriginZygisk) and reinstall Zygisk-based modules (e.g. LSPosed) last. Optional cleanup of leftovers, e.g. APatch: `rm -rf /data/adb/ap /data/adb/apd`.

### 🔍 Checking the kernel after flashing

Root shell (`adb shell` then `su`, or a terminal app):

```sh
uname -r                                              # 4.14.x + FreeRunner name
cat /proc/sys/net/ipv4/tcp_congestion_control         # bbr
cat /proc/sys/net/core/default_qdisc                  # fq
cat /sys/block/zram0/comp_algorithm                   # [lz4] ... zstd
cat /proc/net/ip_tables_targets | grep TTL            # TTL
cat /proc/net/ip6_tables_targets | grep HL            # HL
cat /sys/module/workqueue/parameters/power_efficient  # Y
dmesg | grep -iE "nomount|baseband|susfs" | head      # SuSFS lines (+ NoMount, Baseband Guard with -extras)
ls /proc/self/ns                                      # user net pid uts ipc ... (Droidspaces)
```

In the manager: OriginSU **v4.3.0**, the SuSFS version (`-susfs-v2.4.0` zip: **v2.4.0**), and with an `-extras` zip NoMount shown as available in **OriginMount**. Then check Wi-Fi, mobile data and calls, camera, Bluetooth, fingerprint, audio, charging and overnight battery drain. If something is wrong, save the logs right after reproducing it: `dmesg > /sdcard/dmesg.txt` and `logcat -b all -d > /sdcard/logcat.txt`.

### 🛠️ If a build doesn't boot

Only the Galaxy S10+ has been verified. If a zip doesn't boot on your device:

1. Restore your stock `boot`.
2. Try the `-manual` zip, or a `-susfs-v2.3.0` build (FreeRunner's in-tree SuSFS).
3. If FreeRunner's own build boots but this one doesn't, please report it with your device, ROM, the zip name and, if possible, the logs above.

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

1. **check** — selects the OriginSU tag (`v4.3.0` by default; only `v4.x` OriginSU tags are accepted). Manual runs only.
2. **build** (one job per device, `fail-fast: false`)
   - Clones the FreeRunner branch (default `lineage-24.0` = v3.9) **with its submodules** and downloads the official **LLVM 21.1.8** release (FreeRunner is built with clang 21; the previous "Neutron latest" was a clang 24 dev snapshot).
   - `root = originsu`: removes KernelSU-Next, runs OriginSU's `setup.sh` from tag `v4.3.0` (cloned from the KazeSU repository; the build stops if the tag cannot be checked out), then [`scripts/originsu_compat_4.14.sh`](scripts/originsu_compat_4.14.sh) (4.14 compat for OriginSU) and [`scripts/originsu_hooks_4.14.sh`](scripts/originsu_hooks_4.14.sh), which converts the tree's KSU-Next hooks to what OriginSU expects (see the header of that script: the faccessat/stat argument type mismatch crashed init in SuSFS mode).
   - SuSFS v2.4.0 ([`scripts/susfs_v2.4.sh`](scripts/susfs_v2.4.sh)): removes FreeRunner's in-tree v2.3.0 ([`strip_susfs.py`](scripts/strip_susfs.py), every `#if CONFIG_KSU_SUSFS*` block), applies JackA1ltman's 4.14 v2.4.0 patch hunk by hunk only where all the context matches ([`strict_apply.py`](scripts/strict_apply.py) — `patch --fuzz` put hunks in wrong places on this Samsung tree), then hand-ports the 20 hunks that don't match ([`susfs_v2.4_samsung_fixups.py`](scripts/susfs_v2.4_samsung_fixups.py): Samsung includes, `ida_alloc*` API, smaps). If the set of unmatched hunks ever changes, the build stops instead of guessing.
   - TCP BBR as default congestion control and `fq` as default qdisc, plus the [optimizations](#-optimizations), all checked in the final `.config`.
   - Optional **extra features** ([`scripts/extra_features.sh`](scripts/extra_features.sh)); the build stops if the NoMount driver speaks an API older than the one OriginSU requires (22).
   - Configures like FreeRunner's `build.sh`: `exynos9820-<device>_defconfig` + a config fragment merged with `merge_config.sh`, then checks that every requested option really stuck.
   - Builds with `make LLVM=1` and packages `Image` with LeDrew's AnyKernel, locked to that device.
3. **release** — downloads the matching OriginSU manager APK (arm64-v8a) from the KazeSU repository and publishes `originsu-<tag>` with every device zip, their SHA-256 sums, configs, the manager and a per-device table.

### Manual run options

| Input | Default | Description |
|---|---|---|
| `originsu_ref` | `v4.3.0` | OriginSU tag to build (`v4.x` only) |
| `kernel_branch` | `lineage-24.0` | Branch of the FreeRunner source (Project-Matrixx-New) |
| `device` | `all` | One device or all of them |
| `root` | `originsu` | `originsu`, or `ksunext` = FreeRunner unchanged (control build) |
| `hook_mode` | `susfs` | `susfs` = root + SuSFS; `manual` = root only |
| `susfs_version` | `v2.4.0` | `v2.4.0` = upgraded SuSFS; `intree` = FreeRunner's v2.3.0 (susfs mode only) |
| `extra_features` | `false` | Baseband Guard + NoMount + Droidspaces |
| `kpm` | `false` | Enable `CONFIG_KPM` |
| `publish` | `false` | Publish a GitHub Release |

---

## 🙏 Credits & Acknowledgments

* **[LeDrew2017](https://github.com/LeDrew2017)** & **[Project-Matrixx-New](https://github.com/Project-Matrixx-New)** — For the **FreeRunner** Exynos 9820 kernel source, device support and AnyKernel. **This project is just a rebuild of their work.**
* **[OriginSU](https://github.com/KazeSU/KazeSU/releases/tag/v4.3.0)** (now [KazeSU](https://github.com/KazeSU/KazeSU)) — For the kernel-based root solution used here.
* **[KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next)** — The root solution the original FreeRunner kernel ships with.
* **[simonpunk](https://gitlab.com/simonpunk/susfs4ksu)** — For SuSFS.
* **[JackA1ltman](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)** — For the SuSFS v2.4.0 port to 4.14 and the non-GKI hook layout.
* **[vc-teahouse](https://github.com/vc-teahouse/Baseband-guard)** — For Baseband Guard.
* **[maxsteeel](https://github.com/maxsteeel/nomount)** — For NoMount.
* **[ravindu644](https://github.com/ravindu644/Droidspaces-OSS)** — For Droidspaces.
* **[LLVM](https://github.com/llvm/llvm-project)** — For the Clang toolchain.
* **[tiann/KernelSU](https://github.com/tiann/KernelSU)** — The project OriginSU is built upon.

## 📄 License

Kernel sources are licensed under **GPL-2.0**. See each upstream project for its own license.
