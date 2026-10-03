// nofocus.dylib: loaded into the stock Godot binary by tools/godot_bg.sh (DYLD_INSERT_LIBRARIES).
// Godot 4.7 activates itself on start (show_window -> activateApplication, and the
// "unbundled window activation hack"). No project setting stops that, so this library
// turns the activation calls into no-ops and puts new windows at the back.
// Godot stops drawing when macOS reports its window as fully covered (occlusionState),
// so the library also reports the window as visible and turns App Nap off.
// The game then renders behind other windows and the bridge screenshot works.
#import <AppKit/AppKit.h>
#import <objc/runtime.h>

// A first version blocked focus for the whole run, so the user could not click into the game.
// The blocks only act during the start-up window (Godot activates itself then). After
// NF_GRACE seconds every call goes to the original, so a click can focus the game again.
#define NF_GRACE 6.0
static CFAbsoluteTime nf_start;
static BOOL nf_blocking(void) { return CFAbsoluteTimeGetCurrent() - nf_start < NF_GRACE; }

// Replace an instance method with a block; the block gets the original IMP to fall through to.
static IMP swap_imp(Class c, SEL s, id block) {
	Method m = class_getInstanceMethod(c, s);
	if (!m) return NULL;
	return method_setImplementation(m, imp_implementationWithBlock(block));
}

static OSStatus nf_TransformProcessType(const ProcessSerialNumber *psn, ProcessApplicationTransformState t) {
	if (nf_blocking()) return noErr;
	return TransformProcessType(psn, t);
}
__attribute__((used)) static struct { const void *repl; const void *orig; } nf_interpose[]
	__attribute__((section("__DATA,__interpose"))) = {
	{ (const void *)nf_TransformProcessType, (const void *)TransformProcessType },
};

__attribute__((constructor)) static void nofocus_init(void) {
	nf_start = CFAbsoluteTimeGetCurrent();
	Class app = [NSApplication class];
	static IMP o_aio, o_act, o_raw, o_mkf, o_of, o_ofr;
	o_aio = swap_imp(app, @selector(activateIgnoringOtherApps:), ^(id self, BOOL flag) {
		if (!nf_blocking() && o_aio) ((void (*)(id, SEL, BOOL))o_aio)(self, @selector(activateIgnoringOtherApps:), flag); });
	o_act = swap_imp(app, @selector(activate), ^(id self) {
		if (!nf_blocking() && o_act) ((void (*)(id, SEL))o_act)(self, @selector(activate)); });
	o_raw = swap_imp([NSRunningApplication class], @selector(activateWithOptions:), ^BOOL(id self, NSApplicationActivationOptions o) {
		if (!nf_blocking() && o_raw) return ((BOOL (*)(id, SEL, NSApplicationActivationOptions))o_raw)(self, @selector(activateWithOptions:), o);
		return NO; });
	Class win = [NSWindow class];
	o_mkf = swap_imp(win, @selector(makeKeyAndOrderFront:), ^(NSWindow *self, id sender) {
		if (!nf_blocking() && o_mkf) ((void (*)(id, SEL, id))o_mkf)(self, @selector(makeKeyAndOrderFront:), sender); else [self orderBack:nil]; });
	o_of = swap_imp(win, @selector(orderFront:), ^(NSWindow *self, id sender) {
		if (!nf_blocking() && o_of) ((void (*)(id, SEL, id))o_of)(self, @selector(orderFront:), sender); else [self orderBack:nil]; });
	o_ofr = swap_imp(win, @selector(orderFrontRegardless), ^(NSWindow *self) {
		if (!nf_blocking() && o_ofr) ((void (*)(id, SEL))o_ofr)(self, @selector(orderFrontRegardless)); else [self orderBack:nil]; });
	// Rendering while covered stays on for the whole run (screenshots behind other windows).
	swap_imp(win, @selector(occlusionState), ^NSWindowOcclusionState(NSWindow *self) { return NSWindowOcclusionStateVisible; });
	static id activity;
	activity = [[NSProcessInfo processInfo] beginActivityWithOptions:NSActivityUserInitiatedAllowingIdleSystemSleep
	                                                          reason:@"agent game renders behind other windows"];
}
