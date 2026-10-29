static const uint64_t platform_m20lte_mpidrs[8] = {
	0x100, 0x101, 0x102, 0x103, 0x200, 0x201, 0x0, 0x1
};

static const struct platform platform_m20lte = {
	.name = "m20lte", .io_base = 0x10000000, .io_size = 0x08000000,
	.gic_dist = 0x12301000, .gic_redist = 0x12302000, .gic_v2 = 1, .uart = 0, .log_other_cpu = 1,
	.cores = 8, .mpidrs = platform_m20lte_mpidrs,
	.small_cores = 0x3f,
	.fb_base = 0xEC000000,
	.watch_quietly = 1,
};
