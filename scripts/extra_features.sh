#!/usr/bin/env bash
# Baseband Guard + NoMount + Droidspaces on the Exynos 9820 (4.14) tree.
# Usage (from the kernel root): extra_features.sh <config-fragment-to-append-to>
set -euo pipefail
FRAG="${1:?usage: extra_features.sh <fragment>}"
AUTH=()
[ -n "${GITHUB_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer $GITHUB_TOKEN")

########## 1) Baseband Guard (vc-teahouse) ##########
echo "== Baseband Guard =="
curl -LSs --fail --retry 3 "${AUTH[@]}" \
  "https://raw.githubusercontent.com/vc-teahouse/Baseband-guard/main/setup.sh" | bash \
  || { echo "::error::Baseband Guard setup failed"; exit 1; }
echo "CONFIG_BBG=y" >> "$FRAG"
sed -i 's|^REPO_LINK :=.*|REPO_LINK := https://github.com/vc-teahouse/Baseband-guard|' Baseband-guard/Makefile 2>/dev/null || true
# 4.14 has no CONFIG_LSM / DEFINE_LSM: BBG registers itself with security_add_hooks there.
if grep -q "#define DEFINE_LSM(lsm)" include/linux/lsm_hooks.h 2>/dev/null; then
  echo 'CONFIG_LSM="lockdown,yama,loadpin,safesetid,integrity,selinux,smack,tomoyo,apparmor,bpf,baseband_guard"' >> "$FRAG"
fi
if grep -q "struct[[:space:]]\+task_security_struct[[:space:]]\+\*selinux_cred" security/selinux/include/objsec.h 2>/dev/null; then
  sed -i '/static inline struct task_security_struct \*selinux_cred/,/[[:space:]]*}/d' security/baseband-guard/tracing/tracing.c
fi

########## 2) NoMount (maxsteeel) ##########
echo "== NoMount =="
curl -LSs --fail --retry 3 "${AUTH[@]}" \
  "https://raw.githubusercontent.com/maxsteeel/nomount/refs/heads/master/kernel/setup.sh" | bash -s "v2.3.0-720" \
  || { echo "::error::NoMount setup failed"; exit 1; }
echo "CONFIG_NOMOUNT=y" >> "$FRAG"

########## 3) Droidspaces (ravindu644) ##########
echo "== Droidspaces =="
DS="https://raw.githubusercontent.com/ravindu644/Droidspaces-OSS/refs/heads/main/Documentation/resources/kernel-patches/non-GKI"
apply_ds_patch() {
  local url="$1" desc="$2" f a
  f="$(mktemp)"; a="$(mktemp)"
  curl -LSs --fail --retry 3 -o "$f" "$url" || { echo "::warning::Droidspaces: could not download ${desc}"; rm -f "$f" "$a"; return 0; }
  if patch -p1 --fuzz=5 -t --dry-run < "$f" >/dev/null 2>&1; then
    patch -p1 --fuzz=5 -t < "$f" >/dev/null && echo "-- Droidspaces: applied ${desc}"
  else
    sed 's#kernel/cgroup/cgroup\.c#kernel/cgroup.c#g' "$f" > "$a"
    if ! cmp -s "$f" "$a" && patch -p1 --fuzz=5 -t --dry-run < "$a" >/dev/null 2>&1; then
      patch -p1 --fuzz=5 -t < "$a" >/dev/null && echo "-- Droidspaces: applied ${desc} (single-file cgroup path)"
    else
      echo "::warning::Droidspaces: ${desc} does not apply on this kernel — skipped (configs still enabled)"
    fi
  fi
  rm -f "$f" "$a"
}
[ -f net/netfilter/xt_qtaguid.c ] && apply_ds_patch "$DS/01.fix_kernel_panic_in_xt_qtaguid.patch" "xt_qtaguid panic fix"
apply_ds_patch "$DS/02.fix_restore%20cgroup%20file%20prefix%20handling%20.patch" "cgroup prefix fix"

cat >> "$FRAG" <<'EOF'
CONFIG_SYSVIPC=y
CONFIG_POSIX_MQUEUE=y
CONFIG_NAMESPACES=y
CONFIG_PID_NS=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_NET_NS=y
CONFIG_USER_NS=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_CGROUPS=y
CONFIG_CGROUP_DEVICE=y
CONFIG_CGROUP_SCHED=y
CONFIG_FAIR_GROUP_SCHED=y
CONFIG_CGROUP_FREEZER=y
CONFIG_CGROUP_NET_PRIO=y
CONFIG_MEMCG=y
CONFIG_CFS_BANDWIDTH=y
CONFIG_CGROUP_PIDS=y
CONFIG_CGROUP_CPUACCT=y
CONFIG_DEVTMPFS=y
CONFIG_OVERLAY_FS=y
CONFIG_TMPFS_POSIX_ACL=y
CONFIG_TMPFS_XATTR=y
CONFIG_VETH=y
CONFIG_BRIDGE=y
CONFIG_BRIDGE_NETFILTER=y
CONFIG_NETFILTER_ADVANCED=y
CONFIG_NF_CONNTRACK=y
CONFIG_NF_NAT=y
CONFIG_NF_NAT_REDIRECT=y
CONFIG_IP_NF_IPTABLES=y
CONFIG_IP_NF_FILTER=y
CONFIG_IP_NF_TARGET_MASQUERADE=y
CONFIG_IP_NF_TARGET_REJECT=y
CONFIG_IP6_NF_IPTABLES=y
CONFIG_IP6_NF_FILTER=y
CONFIG_IP6_NF_NAT=y
CONFIG_IP6_NF_TARGET_MASQUERADE=y
CONFIG_NETFILTER_XT_TARGET_MASQUERADE=y
CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y
CONFIG_NETFILTER_XT_MATCH_COMMENT=y
CONFIG_NETFILTER_XT_MATCH_STATE=y
CONFIG_NETFILTER_XT_MATCH_CONNTRACK=y
CONFIG_NETFILTER_XT_MATCH_MULTIPORT=y
CONFIG_NETFILTER_XT_TARGET_REJECT=y
CONFIG_NETFILTER_XT_MATCH_LIMIT=y
CONFIG_NETFILTER_XT_MATCH_OWNER=y
CONFIG_NETFILTER_XT_TARGET_MARK=y
CONFIG_IP_ADVANCED_ROUTER=y
CONFIG_IP_MULTIPLE_TABLES=y
CONFIG_MACVLAN=y
CONFIG_IP_SET=y
CONFIG_NETFILTER_XT_SET=y
EOF
echo "-- extra features added to $FRAG"
