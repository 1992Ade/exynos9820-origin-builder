#!/usr/bin/env bash
# Adapt the KernelSU-Next hooks of the FreeRunner / ProjectMatrixx Exynos 9820 tree
# (Linux 4.14, KSU-Next "legacy-susfs-v2" + in-tree SuSFS v2.1.0) to what OriginSU expects.
#
# Why this is needed (each one is a boot or build killer):
#  * fs/open.c + fs/stat.c: the tree passes `const char __user **` to ksu_handle_faccessat /
#    ksu_handle_stat. With CONFIG_KSU_SUSFS, OriginSU declares those as `struct filename **` and
#    dereferences (*filename)->name -> the kernel reads a user pointer as a struct at the very
#    first faccessat/stat done by init -> PAN fault -> bootloop. In SuSFS mode the hook is moved
#    into a getname()/filename_lookup() block (simonpunk / JackA1ltman 4.14 layout); in manual
#    mode the original __user hooks are kept, because that is the signature OriginSU uses there.
#  * fs/read_write.c, drivers/input/input.c: `ksu_vfs_read_hook` / `ksu_input_hook` are legacy
#    bools that OriginSU rejects at build time (and does not define -> link error). They are
#    replaced by OriginSU's static keys (SuSFS mode) or by an ungated call (manual mode, where
#    OriginSU turns the call into a no-op when its LSM/input_handler auto-hooks are enabled).
#  * kernel/sys.c: OriginSU's SuSFS mode requires a ksu_handle_setresuid() call (not in tree).
#  * security/selinux/hooks.c: ksu_hide_setprocattr() is a KSU-Next-only symbol -> link error.
#  * fs/stat.c: init.rc size fix-up hooks (ksu_handle_vfs_fstat / *_fstat*_ret) are added,
#    otherwise ksud's injected init.rc content can be cut off.
#
# Usage: run from the kernel source root, AFTER OriginSU's setup.sh. Idempotent.
set -euo pipefail

die() { echo "::error::originsu_hooks: $*" >&2; exit 1; }
need() { grep -q "$1" "$2" || die "anchor '$1' not found in $2 (tree layout changed?)"; }
[ -f fs/open.c ] && [ -f drivers/kernelsu/Kconfig ] || die "run from the kernel root after OriginSU setup"

export MARK="/* originsu-hooks-4.14 */"
if grep -qF "$MARK" fs/open.c; then echo "-- originsu hooks already applied"; exit 0; fi

########## fs/filename_lookup must be callable from open.c / stat.c ##########
sed -i 's/^static int filename_lookup(int dfd, struct filename \*name, unsigned flags,/int filename_lookup(int dfd, struct filename *name, unsigned flags,/' fs/namei.c
grep -q '^int filename_lookup(int dfd, struct filename \*name' fs/namei.c || die "could not un-static filename_lookup"

########## fs/open.c (faccessat) ##########
need 'ksu_handle_faccessat(&dfd, &filename, &mode, NULL);' fs/open.c
need 'res = user_path_at(dfd, filename, lookup_flags, &path);' fs/open.c
perl -0pi -e '
  # old KSU-Next extern -> both variants, chosen by mode
  s{#ifdef CONFIG_KSU\n__attribute__\(\(hot\)\)\s*\nextern int ksu_handle_faccessat\(int \*dfd, const char __user \*\*filename_user,\n\s*int \*mode, int \*flags\);\n#endif}{$ENV{MARK}
#if defined(CONFIG_KSU) && defined(CONFIG_KSU_SUSFS)
extern int ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode, int *flags);
extern int filename_lookup(int dfd, struct filename *name, unsigned flags,
			   struct path *path, struct path *root);
#elif defined(CONFIG_KSU)
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode, int *flags);
#endif}s or die "open.c: extern block not found\n";
  # early __user call: manual mode only
  s{#ifdef CONFIG_KSU\n(\s*)ksu_handle_faccessat\(&dfd, &filename, &mode, NULL\);\n#endif}{#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_SUSFS)\n$1ksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n#endif}s or die "open.c: early call not found\n";
  # SuSFS mode: hook on the kernel copy of the name, then look it up
  s{\n(\s*)res = user_path_at\(dfd, filename, lookup_flags, &path\);\n}{
#if defined(CONFIG_KSU) && defined(CONFIG_KSU_SUSFS)
${1}\x7b
$1	struct filename *ksu_fname = getname_flags(filename, lookup_flags, NULL);
$1	ksu_handle_faccessat(&dfd, &ksu_fname, &mode, NULL);
$1	res = filename_lookup(dfd, ksu_fname, lookup_flags, &path, NULL); /* puts the name */
${1}\x7d
#else
$1res = user_path_at(dfd, filename, lookup_flags, &path);
#endif
}s or die "open.c: user_path_at not found\n";
' fs/open.c

########## fs/stat.c (newfstatat / fstatat64 / vfs_statx + fstat size fix-up) ##########
need 'ksu_handle_stat(&dfd, &filename, &flag);' fs/stat.c
need 'error = user_path_at(dfd, filename, lookup_flags, &path);' fs/stat.c
perl -0pi -e '
  s{#if defined\(CONFIG_KSU\)\n__attribute__\(\(hot\)\)\s*\nextern int ksu_handle_stat\(int \*dfd, const char __user \*\*filename_user,\n\s*int \*flags\);\n#endif}{#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_SUSFS)
extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
#endif}s or die "stat.c: extern block not found\n";
  # the two early __user calls: manual mode only
  my $n = (s{#if defined\(CONFIG_KSU\)\n(\s*)ksu_handle_stat\(&dfd, &filename, &flag\);\s*\n#endif}{#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_SUSFS)\n$1ksu_handle_stat(&dfd, &filename, &flag);\n#endif}gs);
  $n >= 1 or die "stat.c: early calls not found\n";
  # helpers + SuSFS-mode prototypes, placed before vfs_statx_fd (first user)
  s{\nint vfs_statx_fd\(unsigned int fd, struct kstat \*stat,}{
$ENV{MARK}
#ifdef CONFIG_KSU
#ifdef CONFIG_KSU_SUSFS
extern struct static_key_true ksu_is_init_rc_hook_enabled;
extern void ksu_handle_vfs_fstat(int fd, loff_t *kstat_size_ptr);
extern int ksu_handle_stat(int *dfd, struct filename **filename, int *flags);
extern int filename_lookup(int dfd, struct filename *name, unsigned flags,
			   struct path *path, struct path *root);
#else
extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);
extern void ksu_handle_fstat64_ret(unsigned long *fd, struct stat64 __user **statbuf_ptr);
#endif
#endif

int vfs_statx_fd(unsigned int fd, struct kstat *stat,}s or die "stat.c: vfs_statx_fd not found\n";
  # SuSFS mode: init.rc size fix-up in vfs_statx_fd
  s{(error = vfs_getattr\(&f\.file->f_path, stat,\n\s*request_mask, query_flags\);\n)(\s*)fdput\(f\);}{$1#if defined(CONFIG_KSU) && defined(CONFIG_KSU_SUSFS)\n$2if (static_branch_unlikely(&ksu_is_init_rc_hook_enabled))\n$2\tksu_handle_vfs_fstat(fd, &stat->size);\n#endif\n$2fdput(f);}s or die "stat.c: vfs_statx_fd body not found\n";
  # SuSFS mode: stat hook on the kernel copy of the name in vfs_statx
  s{\n(\s*)error = user_path_at\(dfd, filename, lookup_flags, &path\);\n}{
#if defined(CONFIG_KSU) && defined(CONFIG_KSU_SUSFS)
${1}\x7b
$1	struct filename *ksu_fname = getname_flags(filename, lookup_flags, NULL);
$1	int ksu_flags = flags;
$1	ksu_handle_stat(&dfd, &ksu_fname, &ksu_flags);
$1	error = filename_lookup(dfd, ksu_fname, lookup_flags, &path, NULL); /* puts the name */
${1}\x7d
#else
$1error = user_path_at(dfd, filename, lookup_flags, &path);
#endif
}s or die "stat.c: vfs_statx user_path_at not found\n";
  # manual mode: fstat return hooks
  # (after cp_new_stat*: they patch st_size in the user buffer)
  s{(SYSCALL_DEFINE2\(newfstat, unsigned int, fd, struct stat __user \*, statbuf\)\n\{\n\s*struct kstat stat;\n\s*int error = vfs_fstat\(fd, &stat\);\n\s*\n\s*if \(!error\)\n\s*error = cp_new_stat\(&stat, statbuf\);\n)}{$1#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_SUSFS)\n\tksu_handle_newfstat_ret(&fd, &statbuf);\n#endif\n}s or die "stat.c: newfstat not found\n";
  s{(SYSCALL_DEFINE2\(fstat64, unsigned long, fd, struct stat64 __user \*, statbuf\)\n\{\n\s*struct kstat stat;\n\s*int error = vfs_fstat\(fd, &stat\);\n\s*\n\s*if \(!error\)\n\s*error = cp_new_stat64\(&stat, statbuf\);\n)}{$1#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_SUSFS)\n\tksu_handle_fstat64_ret(&fd, &statbuf);\n#endif\n}s;
' fs/stat.c

########## fs/read_write.c (init.rc hook: legacy bool -> OriginSU static key) ##########
need 'ksu_vfs_read_hook' fs/read_write.c
perl -0pi -e '
  s{extern bool ksu_vfs_read_hook __read_mostly;\nextern __attribute__\(\(cold\)\) int ksu_handle_sys_read\(unsigned int fd,\nchar __user \*\*buf_ptr, size_t \*count_ptr\);}{#ifdef CONFIG_KSU_SUSFS
extern struct static_key_true ksu_is_init_rc_hook_enabled;
#endif
extern int ksu_handle_sys_read(unsigned int fd, char __user **buf_ptr, size_t *count_ptr);}s or die "read_write.c: extern block not found\n";
  s{if \(unlikely\(ksu_vfs_read_hook\)\)\nksu_handle_sys_read\(fd, &buf, &count\);}{#ifdef CONFIG_KSU_SUSFS
	if (static_branch_unlikely(&ksu_is_init_rc_hook_enabled))
#endif
		ksu_handle_sys_read(fd, &buf, &count);}s or die "read_write.c: call not found\n";
' fs/read_write.c
grep -qw ksu_vfs_read_hook fs/read_write.c && die "ksu_vfs_read_hook still present"

########## drivers/input/input.c (volume-down safe mode: legacy bool -> static key) ##########
need 'ksu_input_hook' drivers/input/input.c
perl -0pi -e '
  s{extern bool ksu_input_hook __read_mostly;\n}{#ifdef CONFIG_KSU_SUSFS\nextern struct static_key_true ksu_is_input_hook_enabled;\n#endif\n}s or die "input.c: extern not found\n";
  s{(\s*)if \(unlikely\(ksu_input_hook\)\)\n(\s*ksu_handle_input_handle_event\(&type, &code, &value\);)}{\n#ifdef CONFIG_KSU_SUSFS$1if (static_branch_unlikely(&ksu_is_input_hook_enabled))\n#endif\n$2}s or die "input.c: call not found\n";
' drivers/input/input.c
grep -qw ksu_input_hook drivers/input/input.c && die "ksu_input_hook still present"

########## kernel/sys.c (setresuid hook, required in SuSFS mode) ##########
if ! grep -q ksu_handle_setresuid kernel/sys.c; then
  need 'SYSCALL_DEFINE3(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid)' kernel/sys.c
  perl -0pi -e '
    s{\nSYSCALL_DEFINE3\(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid\)\n\{\n}{
#ifdef CONFIG_KSU
extern int ksu_handle_setresuid(uid_t ruid, uid_t euid, uid_t suid);
#endif
SYSCALL_DEFINE3(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid)
\{
}s or die "sys.c: setresuid not found\n";
    s{(SYSCALL_DEFINE3\(setresuid, uid_t, ruid, uid_t, euid, uid_t, suid\).*?ksuid = make_kuid\(ns, suid\);\n)}{$1#ifdef CONFIG_KSU_SUSFS\n\tksu_handle_setresuid(ruid, euid, suid);\n#endif\n}s or die "sys.c: make_kuid anchor not found\n";
  ' kernel/sys.c
fi

########## security/selinux/hooks.c (KSU-Next only symbol) ##########
if grep -q ksu_hide_setprocattr security/selinux/hooks.c; then
  perl -0pi -e '
    s{#ifdef CONFIG_KSU\nextern int ksu_hide_setprocattr\(const char \*name, void \*value, size_t size\);\n#endif\n}{}s;
    s{\s*#ifdef CONFIG_KSU\n\s*ksu_hide_setprocattr\(name, value, size\);\n\s*#endif\n}{\n}s;
  ' security/selinux/hooks.c
  grep -q ksu_hide_setprocattr security/selinux/hooks.c && die "ksu_hide_setprocattr still present"
fi

echo "-- originsu hooks (4.14) applied:"
for p in kernel/sys.c:ksu_handle_setresuid fs/exec.c:ksu_handle_execveat fs/open.c:ksu_handle_faccessat \
         fs/read_write.c:ksu_handle_sys_read fs/stat.c:ksu_handle_stat kernel/reboot.c:ksu_handle_sys_reboot \
         drivers/input/input.c:ksu_handle_input_handle_event fs/stat.c:ksu_handle_vfs_fstat; do
  printf '   %-24s %-32s x%s\n' "${p%%:*}" "${p#*:}" "$(grep -c "${p#*:}" "${p%%:*}")"
done
