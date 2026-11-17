#!/usr/bin/env python3
"""Hand ports of the SuSFS v2.4.0 (JackA1ltman 4.14 patch) hunks that strict_apply.py cannot place
on the FreeRunner / Samsung Exynos 9820 tree.

None of these hunks carries new v2.4.0 code (all identical to v2.3.0, checked hunk by hunk): they
only fail because the Samsung tree differs around them (extra includes, CONFIG_RKP_NS_PROT
variants, the newer ida_alloc*/ida_free API, Samsung-only lines in smaps/uname). The ida-based
ones follow FreeRunner's own v2.3.0 adaptation of the same functions.

Each edit is anchored on exact text and must match exactly once; anything else aborts the build.
Hunks that only add/remove a blank line (namespace #4, task_mmu #5/#6) are skipped on purpose.

Usage: susfs_v2.4_samsung_fixups.py <kernel-root>     (after strip_susfs.py + strict_apply.py)
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])


def edit(path, old, new, what):
    p = ROOT / path
    s = p.read_text(errors="surrogateescape")
    if new in s:
        print(f"   = {path}: {what} (already there)")
        return
    n = s.count(old)
    if n != 1:
        sys.exit(f"::error::susfs fixups: {path}: anchor for '{what}' found {n} times")
    p.write_text(s.replace(old, new, 1), errors="surrogateescape")
    print(f"   + {path}: {what}")


def after(path, anchor, block, what):
    edit(path, anchor, anchor + block, what)


def before(path, anchor, block, what):
    edit(path, anchor, block + anchor, what)


INC = "#ifdef {g}\n#include <linux/susfs_def.h>\n#endif // #ifdef {g}\n"

# ---- includes (Samsung include lists differ) ------------------------------------------
after("fs/namei.c", "#include <linux/uaccess.h>\n", INC.format(g="CONFIG_KSU_SUSFS"), "namei #1 include")
after("fs/proc/base.c", "#include <linux/cpufreq_times.h>\n",
      "#if defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n"
      "#include <linux/susfs_def.h>\n"
      "#endif // #if defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n",
      "proc/base #1 include")
after("fs/proc/task_mmu.c", "#include <linux/ctype.h>\n",
      "#if defined(CONFIG_KSU_SUSFS_SUS_KSTAT) || defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n"
      "#include <linux/susfs_def.h>\n"
      "#endif // #if defined(CONFIG_KSU_SUSFS_SUS_KSTAT) || defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n",
      "task_mmu #1 include")
after("kernel/kallsyms.c", "#include <linux/compiler.h>\n",
      INC.format(g="CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS"), "kallsyms #1 include")
after("mm/memory.c", "#include <asm/pgtable.h>\n",
      "\n" + INC.format(g="CONFIG_KSU_SUSFS_SUS_MAP"), "memory #1 include")
after("fs/namespace.c", "#include <linux/sched/task.h>\n", INC.format(g="CONFIG_KSU_SUSFS"),
      "namespace #1 include")
after("fs/namespace.c", '#include "pnode.h"\n#include "internal.h"\n', """
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
extern bool susfs_is_current_ksu_domain(void);
extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;

#define CL_COPY_MNT_NS BIT(25) /* used by copy_mnt_ns() */

#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
""", "namespace #1 externs")

# ---- fs/namei.c #21: open redirect in do_o_path (vfs_open() has 2 args on this tree) -----
edit("fs/namei.c", """static int do_o_path(struct nameidata *nd, unsigned flags, struct file *file)
{
	struct path path;
	int error = path_lookupat(nd, flags, &path);
	if (!error) {
		audit_inode(nd->name, path.dentry, 0);""", """static int do_o_path(struct nameidata *nd, unsigned flags, struct file *file)
{
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
	int old_dfd = nd->dfd;
	struct filename *fake_filename = NULL;
#endif // #ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
	struct path path;
	int error = path_lookupat(nd, flags, &path);
	if (!error) {
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		if (old_dfd != -1 &&
			SUSFS_IS_INODE_OPEN_REDIRECT_WITHOUT_UID_CHECK(path.dentry->d_inode))
		{
			fake_filename = susfs_open_redirect_spoof_do_sys_openat(path.dentry->d_inode);
			if (fake_filename && !IS_ERR(fake_filename)) {
				struct path fake_path;

				/* filename_lookup() consumes fake_filename */
				error = filename_lookup(old_dfd, fake_filename, flags, &fake_path, NULL);
				path_put(&path);
				if (unlikely(error))
					return error;
				path = fake_path;
			}
		}
#endif // #ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		audit_inode(nd->name, path.dentry, 0);""", "namei #21 do_o_path open redirect")

# ---- fs/namespace.c: mount id / group id (ida_alloc*/ida_free API) ---------------------
edit("fs/namespace.c", """static void mnt_free_id(struct mount *mnt)
{
	ida_free(&mnt_id_ida, mnt->mnt_id);""", """static void mnt_free_id(struct mount *mnt)
{
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (unlikely(mnt->mnt.mnt_flags & VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT))
		return;

#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	ida_free(&mnt_id_ida, mnt->mnt_id);""", "namespace #2 mnt_free_id")

edit("fs/namespace.c", """static int mnt_alloc_group_id(struct mount *mnt)
{
	int res = ida_alloc_min(&mnt_group_ida, 1, GFP_KERNEL);
""", """static int mnt_alloc_group_id(struct mount *mnt)
{
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	int res;

	if (susfs_is_current_ksu_domain()) {
		res = ida_alloc_min(&mnt_group_ida, DEFAULT_KSU_MNT_GROUP_ID, GFP_KERNEL);
		goto bypass_orig_flow;
	}
	res = ida_alloc_min(&mnt_group_ida, 1, GFP_KERNEL);
bypass_orig_flow:
#else
	int res = ida_alloc_min(&mnt_group_ida, 1, GFP_KERNEL);
#endif
""", "namespace #3 mnt_alloc_group_id")

# #5: the two fake-mnt_id allocators (v2.4.0 code, ida_simple_get -> ida_alloc_min)
ALLOC = """#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
/* A copy of alloc_vfsmnt() but allocates the fake mnt_id for mounts
 * that are unshared by ksu process
 */
static struct mount *susfs_alloc_unshare_ksu_vfsmnt(const char *name, int old_mnt_id)
{
	struct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);

	if (mnt) {
		mnt->mnt_id = old_mnt_id;

		if (name) {
			mnt->mnt_devname = kstrdup_const(name, GFP_KERNEL_ACCOUNT);
			if (!mnt->mnt_devname)
				goto out_free_cache;
		}

#ifdef CONFIG_SMP
		mnt->mnt_pcp = alloc_percpu(struct mnt_pcp);
		if (!mnt->mnt_pcp)
			goto out_free_devname;

		this_cpu_add(mnt->mnt_pcp->mnt_count, 1);
#else
		mnt->mnt_count = 1;
		mnt->mnt_writers = 0;
#endif

		INIT_HLIST_NODE(&mnt->mnt_hash);
		INIT_LIST_HEAD(&mnt->mnt_child);
		INIT_LIST_HEAD(&mnt->mnt_mounts);
		INIT_LIST_HEAD(&mnt->mnt_list);
		INIT_LIST_HEAD(&mnt->mnt_expire);
		INIT_LIST_HEAD(&mnt->mnt_share);
		INIT_LIST_HEAD(&mnt->mnt_slave_list);
		INIT_LIST_HEAD(&mnt->mnt_slave);
		INIT_HLIST_NODE(&mnt->mnt_mp_list);
		INIT_LIST_HEAD(&mnt->mnt_umounting);
		init_fs_pin(&mnt->mnt_umount, drop_mountpoint);
	}
	return mnt;

#ifdef CONFIG_SMP
out_free_devname:
	kfree_const(mnt->mnt_devname);
#endif
out_free_cache:
	kmem_cache_free(mnt_cache, mnt);
	return NULL;
}
/* A copy of alloc_vfsmnt() but allocates the fake mnt_id for mount
 * that is mounted or single cloned by ksu process
 */
static struct mount *susfs_alloc_non_unshare_ksu_vfsmnt(const char *name)
{
	struct mount *mnt = kmem_cache_zalloc(mnt_cache, GFP_KERNEL);
	int res;

	if (mnt) {
		res = ida_alloc_min(&mnt_id_ida, DEFAULT_KSU_MNT_ID, GFP_KERNEL);
		if (res < 0)
			goto out_free_cache;

		mnt->mnt_id = res;

		if (name) {
			mnt->mnt_devname = kstrdup_const(name, GFP_KERNEL_ACCOUNT);
			if (!mnt->mnt_devname)
				goto out_free_id;
		}

#ifdef CONFIG_SMP
		mnt->mnt_pcp = alloc_percpu(struct mnt_pcp);
		if (!mnt->mnt_pcp)
			goto out_free_devname;

		this_cpu_add(mnt->mnt_pcp->mnt_count, 1);
#else
		mnt->mnt_count = 1;
		mnt->mnt_writers = 0;
#endif

		INIT_HLIST_NODE(&mnt->mnt_hash);
		INIT_LIST_HEAD(&mnt->mnt_child);
		INIT_LIST_HEAD(&mnt->mnt_mounts);
		INIT_LIST_HEAD(&mnt->mnt_list);
		INIT_LIST_HEAD(&mnt->mnt_expire);
		INIT_LIST_HEAD(&mnt->mnt_share);
		INIT_LIST_HEAD(&mnt->mnt_slave_list);
		INIT_LIST_HEAD(&mnt->mnt_slave);
		INIT_HLIST_NODE(&mnt->mnt_mp_list);
		INIT_LIST_HEAD(&mnt->mnt_umounting);
		init_fs_pin(&mnt->mnt_umount, drop_mountpoint);
	}
	return mnt;

#ifdef CONFIG_SMP
out_free_devname:
	kfree_const(mnt->mnt_devname);
#endif
out_free_id:
	mnt_free_id(mnt);
out_free_cache:
	kmem_cache_free(mnt_cache, mnt);
	return NULL;
}
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT

"""
before("fs/namespace.c", "static struct mount *alloc_vfsmnt(const char *name)\n", ALLOC,
       "namespace #5 fake mnt_id allocators")

# #6: hide ksu mounts from zygote_next / umounted processes in __lookup_mnt
edit("fs/namespace.c", """	struct hlist_head *head = m_hash(mnt, dentry);
	struct mount *p;


	hlist_for_each_entry_rcu(p, head, mnt_hash)
#ifdef CONFIG_RKP_NS_PROT""", """	struct hlist_head *head = m_hash(mnt, dentry);
	struct mount *p;

#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) && !defined(CONFIG_RKP_NS_PROT)
	// - The hook here is needed as a temp solution to hide sus mnts for zygote_next
	//   spawned process since it just inherits the init mount namespace, and here
	//   we also spoof for the zygote spawned processes that are marked umounted,
	//   with this hack, we do not even need to umount those sus mounts.
	// - The solution here is simply to return the legit mount.
	if (susfs_is_current_proc_umounted()) {
		hlist_for_each_entry_rcu(p, head, mnt_hash)
			if (p->mnt_id < DEFAULT_KSU_MNT_ID && &p->mnt_parent->mnt == mnt && p->mnt_mountpoint == dentry)
				return p;
		return NULL;
	}
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT

	hlist_for_each_entry_rcu(p, head, mnt_hash)
#ifdef CONFIG_RKP_NS_PROT""", "namespace #6 __lookup_mnt")

# #8: fake mnt_id for mounts cloned by ksu processes (clone_mnt)
edit("fs/namespace.c", """#ifdef CONFIG_RKP_NS_PROT
	int nsflags;
#endif

	mnt = alloc_vfsmnt(old->mnt_devname);
	if (!mnt)
		return ERR_PTR(-ENOMEM);
""", """#ifdef CONFIG_RKP_NS_PROT
	int nsflags;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	bool is_mnt_ksu_unshared = false;

	// - We will just stop checking for ksu process if /sdcard/Android is accessible,
	//   for the sake of performance
	if (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {
	// - If /sdcard/Android is still not accessible, we keep checking for mounts
	//   mounted by ksu process
		if (susfs_is_current_ksu_domain()) {
			// - If it is unsharing, we re-use the old->mnt_id assign it for mnt->mnt_id directly
			//   without going thru ida, but we need to set a bit VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT
			//   on mnt->mnt.mnt_flags below, otherwise we find no other ways to identify if this
			//   mnt->mnt_id is assigned without ida when it is being freed in mnt_free_id().
			if (flag & CL_COPY_MNT_NS) {
				mnt = susfs_alloc_unshare_ksu_vfsmnt(old->mnt_devname, old->mnt_id);
				is_mnt_ksu_unshared = true;
				goto bypass_orig_flow;
			}
			// else we just go assign fake mnt_id starting with DEFAULT_KSU_MNT_ID
			mnt = susfs_alloc_non_unshare_ksu_vfsmnt(old->mnt_devname);
			goto bypass_orig_flow;
		}
	}
	// - We keep checking all processes and if old->mnt_id >= DEFAULT_KSU_MNT_ID,
	//   go assign fake mnt_id starting with DEFAULT_KSU_MNT_ID
	if (old->mnt_id >= DEFAULT_KSU_MNT_ID) {
		mnt = susfs_alloc_non_unshare_ksu_vfsmnt(old->mnt_devname);
		goto bypass_orig_flow;
	}
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT

	mnt = alloc_vfsmnt(old->mnt_devname);
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
bypass_orig_flow:
#endif
	if (!mnt)
		return ERR_PTR(-ENOMEM);
""", "namespace #8 clone_mnt")

# #10: tag namespace copies (copy_mnt_ns)
edit("fs/namespace.c", """	if (user_ns != ns->user_ns)
		copy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;
#ifdef CONFIG_RKP_NS_PROT
	new = copy_tree(old, old->mnt->mnt_root, copy_flags);""", """	if (user_ns != ns->user_ns)
		copy_flags |= CL_SHARED_TO_SLAVE | CL_UNPRIVILEGED;
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	copy_flags |= CL_COPY_MNT_NS;
#endif
#ifdef CONFIG_RKP_NS_PROT
	new = copy_tree(old, old->mnt->mnt_root, copy_flags);""", "namespace #10 copy_mnt_ns")

# ---- fs/proc/task_mmu.c ---------------------------------------------------------------
before("fs/proc/task_mmu.c", "static void\nshow_map_vma(struct seq_file *m, struct vm_area_struct *vma", """#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
extern void susfs_sus_kstat_spoof_show_map_vma(struct inode *inode, dev_t *out_dev, unsigned long *out_ino);
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
extern struct srcu_struct susfs_srcu_open_redirect;
extern int susfs_open_redirect_spoof_show_map_vma_srcu(struct inode *inode, unsigned long *out_ino, dev_t *out_dev, char **out_spoofed_name);
#endif // #ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT

""", "task_mmu #2 externs")
# (this tree splits show_smap() like newer kernels: the check goes in show_smap(), before
#  smap_gather_stats(), as in FreeRunner's own port)
before("fs/proc/task_mmu.c", "\tsmap_gather_stats(vma, &mss);\n\n\tshow_map_vma(m, vma);", """#ifdef CONFIG_KSU_SUSFS_SUS_MAP
	if (vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))
		return 0;
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MAP

""", "task_mmu #4 show_smap sus_map")

# ---- fs/stat.c: STATX_SUS_KSTAT / susfs_is_current_app_uid() come from susfs_def.h
#      (JackA1ltman adds this include in his separate hook script) -------------------------
after("fs/stat.c", "#include <asm/unistd.h>\n", INC.format(g="CONFIG_KSU_SUSFS"), "stat include susfs_def.h")

# ---- fs/super.c #2: fake minor dev for ksu mounts (ida_alloc_range API) -----------------
edit("fs/super.c", """int get_anon_bdev(dev_t *p)
{
	int dev;
""", """int get_anon_bdev(dev_t *p)
{
	int dev;

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {
		if (susfs_is_current_ksu_domain()) {
			dev = ida_alloc_range(&unnamed_dev_ida, DEFAULT_KSU_MNT_MINOR_DEV,
					      (1 << MINORBITS) - 1, GFP_ATOMIC);
			if (dev == -ENOSPC)
				dev = -EMFILE;
			if (dev < 0)
				return dev;

			*p = MKDEV(0, dev);
			return 0;
		}
	}
#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
""", "super #2 get_anon_bdev")

# ---- kernel/sys.c #4: uname spoofing (FreeRunner's bpfloader fake-uname kept after it) ----
edit("kernel/sys.c", """SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)
{
	struct new_utsname tmp;

	down_read(&uts_sem);
	memcpy(&tmp, utsname(), sizeof(tmp));
""", """#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
extern struct static_key_false susfs_is_uname_spoof_buffer_set;
extern void susfs_spoof_uname(struct new_utsname* tmp);
#endif
SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)
{
	struct new_utsname tmp;

	down_read(&uts_sem);
	memcpy(&tmp, utsname(), sizeof(tmp));
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
	if (static_branch_likely(&susfs_is_uname_spoof_buffer_set))
		susfs_spoof_uname(&tmp);
#endif
""", "sys #4 newuname spoof")

print("-- SuSFS v2.4.0 Samsung fixups applied")
