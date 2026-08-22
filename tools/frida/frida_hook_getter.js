/**
 * IL2CPP Export Enumerator & Safe Class Discovery
 */

'use strict';

function run() {
    var libil2cpp = Process.findModuleByName('libil2cpp.so');
    var liblogic = Process.findModuleByName('liblogic.so');

    console.log('[*] Enumerating libil2cpp exports...');
    var exports = libil2cpp.enumerateExports();
    console.log('[+] libil2cpp.so export count: ' + exports.length);

    var interesting = [];
    exports.forEach(function(exp) {
        if (exp.name.indexOf('il2cpp_') === 0) {
            interesting.push(exp.name);
        }
    });
    console.log('[+] IL2CPP C APIs: ' + interesting.slice(0, 20).join(', ') + ' ... (' + interesting.length + ' total)');

    // Test il2cpp_domain_get
    var p_domain_get = libil2cpp.findExportByName('il2cpp_domain_get');
    if (p_domain_get) {
        try {
            var fn_domain_get = new NativeFunction(p_domain_get, 'pointer', []);
            var dom = fn_domain_get();
            console.log('[+] il2cpp_domain_get() -> ' + dom);
        } catch(e) {
            console.log('[-] domain_get error: ' + e);
        }
    }

    // Direct string / memory scan for Il2CppClass of LogicBattleManager
    // In Unity, Il2CppClass has name pointer at +0x10 and namespace at +0x18
    // We can hook LogicBattleManager.get_m_LocalPlayerLogic (which still works at RVA 0x1648e7c)
    // When called, X0 IS THE EXACT INSTANCE OF LogicBattleManager!
    // And its dereference [X0] IS the Il2CppClass of LogicBattleManager!
    var rva_getLocal = ptr('0x1648e7c');
    var addr_getLocal = liblogic.base.add(rva_getLocal);
    console.log('[+] Hooking get_m_LocalPlayerLogic at ' + addr_getLocal + ' (RVA 0x1648e7c)...');

    try {
        Interceptor.attach(addr_getLocal, {
            onEnter: function(args) {
                var mgrInstance = this.context.x0;
                console.log('\n[🔥 INTERCEPTED get_m_LocalPlayerLogic 🔥]');
                console.log('[+] LogicBattleManager Instance: ' + mgrInstance);
                if (!mgrInstance.isNull()) {
                    var mgrKlass = mgrInstance.readPointer();
                    console.log('[+] LogicBattleManager Il2CppClass: ' + mgrKlass);
                    
                    var namePtr = mgrKlass.add(0x10).readPointer();
                    var nsPtr = mgrKlass.add(0x18).readPointer();
                    console.log('[+] Class Name: ' + (namePtr.isNull() ? 'null' : namePtr.readUtf8String()));
                    console.log('[+] Namespace : ' + (nsPtr.isNull() ? 'null' : nsPtr.readUtf8String()));

                    // Check static_fields
                    var sf_b0 = mgrKlass.add(0xb0).readPointer();
                    var sf_b8 = mgrKlass.add(0xb8).readPointer();
                    console.log('[+] static_fields (+0xb0): ' + sf_b0);
                    console.log('[+] static_fields (+0xb8): ' + sf_b8);

                    // Check fields on manager instance
                    var state = mgrInstance.add(0x180).readS32();
                    var frameTime = mgrInstance.add(0x19c).readU32();
                    var selfPlayer = mgrInstance.add(0x200).readPointer();
                    var localLogic = mgrInstance.add(0x0a0).readPointer();
                    var dicPlayer = mgrInstance.add(0x0a8).readPointer();
                    console.log('[+] _m_eState (+0x180)   : ' + state + (state === 2 ? ' (IN_BATTLE ✅)' : ''));
                    console.log('[+] m_uiFrameTime (+0x19c): ' + frameTime);
                    console.log('[+] m_RealSelfPlayer (+0x200): ' + selfPlayer);
                    console.log('[+] m_LocalPlayerLogic (+0x0a0): ' + localLogic);
                    console.log('[+] m_dicPlayerLogic (+0x0a8): ' + dicPlayer);

                    if (!selfPlayer.isNull()) {
                        console.log('[+] Local Hero ID: ' + selfPlayer.add(0xac).readS32() + ', HP: ' + selfPlayer.add(0xc8).readS32() + '/' + selfPlayer.add(0xcc).readS32());
                        console.log('[+] Local Pos: (' + selfPlayer.add(0x268).readDouble().toFixed(2) + ', ' + selfPlayer.add(0x270).readDouble().toFixed(2) + ')');
                    }
                }
            }
        });
        console.log('[+] Interceptor attached! Waiting for match ticks...');
    } catch(e) {
        console.log('[-] Failed to attach Interceptor: ' + e);
    }
}

setTimeout(run, 100);
