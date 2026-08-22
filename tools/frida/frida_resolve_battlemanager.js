/**
 * Frida Script: Resolve LogicBattleManager Singleton
 * 
 * Hooks LogicBattleData.get_battleManager() and LogicBattleManager.get_m_LocalPlayerLogic()
 * to discover their runtime return values. These are then compared against what the
 * static resolution chain in orchestrator.py produces.
 *
 * Usage: frida -U -n com.mobile.legends -l frida_resolve_battlemanager.js
 *    or: frida -H 127.0.0.1 -n com.mobile.legends -l frida_resolve_battlemanager.js
 */

'use strict';

function findLiblogicBase() {
    var modules = Process.enumerateModules();
    for (var i = 0; i < modules.length; i++) {
        if (modules[i].name === 'liblogic.so') {
            return modules[i].base;
        }
    }
    return null;
}

function main() {
    var liblogicBase = findLiblogicBase();
    if (!liblogicBase) {
        console.log('[!] liblogic.so NOT found in process. Is a match active?');
        // Retry after a delay — the library may load later
        setTimeout(main, 3000);
        return;
    }

    console.log('[*] liblogic.so base: ' + liblogicBase);

    // RVA for LogicBattleData.get_battleManager
    var rva_getBattleManager = 0x10c0774;
    var addr_getBattleManager = liblogicBase.add(rva_getBattleManager);
    console.log('[*] LogicBattleData.get_battleManager @ ' + addr_getBattleManager);

    // RVA for LogicBattleManager.get_m_LocalPlayerLogic
    var rva_getLocalPlayer = 0x1648e7c;
    var addr_getLocalPlayer = liblogicBase.add(rva_getLocalPlayer);
    console.log('[*] LogicBattleManager.get_m_LocalPlayerLogic @ ' + addr_getLocalPlayer);

    // === Hook 1: get_battleManager ===
    try {
        Interceptor.attach(addr_getBattleManager, {
            onEnter: function(args) {
                // No args needed — static getter
            },
            onLeave: function(retval) {
                if (!retval.isNull()) {
                    console.log('[HOOK] get_battleManager() returned: ' + retval);

                    // Read _m_eState (+0x180) to confirm InBattle
                    try {
                        var state = retval.add(0x180).readS32();
                        console.log('[HOOK]   _m_eState = ' + state + (state === 2 ? ' (InBattle ✅)' : ' (NOT InBattle)'));
                    } catch(e) {}

                    // Read m_uiFrameTime (+0x19c)
                    try {
                        var ft = retval.add(0x19c).readU32();
                        console.log('[HOOK]   m_uiFrameTime = ' + ft);
                    } catch(e) {}

                    // Read m_RealSelfPlayer (+0x200)
                    try {
                        var selfPlayer = retval.add(0x200).readPointer();
                        console.log('[HOOK]   m_RealSelfPlayer (+0x200) = ' + selfPlayer);
                        if (!selfPlayer.isNull()) {
                            // Read hero ID at +0xac
                            var heroId = selfPlayer.add(0xac).readS32();
                            console.log('[HOOK]     heroId = ' + heroId);
                            // Read HP at +0xc8
                            var hp = selfPlayer.add(0xc8).readS32();
                            var hpMax = selfPlayer.add(0xcc).readS32();
                            console.log('[HOOK]     HP = ' + hp + '/' + hpMax);
                            // Read position
                            var posX = selfPlayer.add(0x268).readDouble();
                            var posY = selfPlayer.add(0x270).readDouble();
                            console.log('[HOOK]     Position = (' + posX.toFixed(1) + ', ' + posY.toFixed(1) + ')');
                            // Read level
                            var level = selfPlayer.add(0xb4).readS32();
                            console.log('[HOOK]     Level = ' + level);
                            // Read camp
                            var camp = selfPlayer.add(0x1dc).readS32();
                            console.log('[HOOK]     Camp = ' + camp);
                        }
                    } catch(e) {
                        console.log('[HOOK]   m_RealSelfPlayer read error: ' + e);
                    }

                    // Read m_LocalPlayerLogic (+0x0a0)
                    try {
                        var localLogic = retval.add(0x0a0).readPointer();
                        console.log('[HOOK]   m_LocalPlayerLogic (+0x0a0) = ' + localLogic);
                    } catch(e) {}

                    // Read m_dicPlayerLogic (+0x0a8)
                    try {
                        var dicPtr = retval.add(0x0a8).readPointer();
                        console.log('[HOOK]   m_dicPlayerLogic (+0x0a8) = ' + dicPtr);
                        if (!dicPtr.isNull()) {
                            var count = dicPtr.add(0x20).readS32();
                            console.log('[HOOK]     Player count = ' + count);
                        }
                    } catch(e) {}
                } else {
                    console.log('[HOOK] get_battleManager() returned NULL');
                }
            }
        });
        console.log('[*] Hooked get_battleManager ✅');
    } catch(e) {
        console.log('[!] Failed to hook get_battleManager: ' + e);
    }

    // === Hook 2: get_m_LocalPlayerLogic ===
    try {
        Interceptor.attach(addr_getLocalPlayer, {
            onEnter: function(args) {
                this.mgr = this.context.x0;  // First arg is 'this' (LogicBattleManager instance)
            },
            onLeave: function(retval) {
                if (!retval.isNull()) {
                    console.log('[HOOK] get_m_LocalPlayerLogic(mgr=' + this.mgr + ') returned: ' + retval);
                }
            }
        });
        console.log('[*] Hooked get_m_LocalPlayerLogic ✅');
    } catch(e) {
        console.log('[!] Failed to hook get_m_LocalPlayerLogic: ' + e);
    }

    // === One-shot: Walk the static resolution chain manually ===
    console.log('\n[*] === Manual Static Chain Walk ===');
    try {
        // Step 1: Read the instructions at RVA+0x10
        var codeAddr = addr_getBattleManager.add(0x10);
        var insn_adrp = codeAddr.readU32();
        var insn_ldr = codeAddr.add(4).readU32();
        console.log('[CHAIN] Instruction at RVA+0x10: ADRP = 0x' + insn_adrp.toString(16));
        console.log('[CHAIN] Instruction at RVA+0x14: LDR  = 0x' + insn_ldr.toString(16));

        // Step 2: Decode ADRP
        if ((insn_adrp & 0x9f000000) === 0x90000000) {
            var immlo = (insn_adrp >>> 29) & 0x3;
            var immhi = (insn_adrp >>> 5) & 0x7ffff;
            var imm = (immhi << 2) | immlo;
            if (imm & 0x100000) imm -= 0x200000;
            var pc_adrp = codeAddr;
            // ADRP uses page-aligned PC
            var page_target_num = (pc_adrp.toInt32 ? Number(BigInt(pc_adrp.toString()) & ~BigInt(0xfff)) : 0);

            // Use pointer arithmetic for 64-bit safety
            var pc_page = ptr(pc_adrp.toString()).and(ptr('0xfffffffffffff000'));
            var page_target = pc_page.add(imm << 12);
            console.log('[CHAIN] ADRP page target: ' + page_target);

            // Step 3: Decode LDR offset
            if ((insn_ldr & 0xffc00000) === 0xf9400000) {
                var imm12 = (insn_ldr >>> 10) & 0xfff;
                var ldr_offset = imm12 * 8;
                var got_target = page_target.add(ldr_offset);
                console.log('[CHAIN] LDR offset: 0x' + ldr_offset.toString(16) + ' → GOT @ ' + got_target);

                // Step 4: Read GOT entry (should be Il2CppClass*)
                var klass_ptr = got_target.readPointer();
                console.log('[CHAIN] GOT → klass (Il2CppClass*): ' + klass_ptr);

                if (!klass_ptr.isNull()) {
                    // Step 5: Read static_fields at both +0xb0 and +0xb8
                    var sf_b0 = klass_ptr.add(0xb0).readPointer();
                    var sf_b8 = klass_ptr.add(0xb8).readPointer();
                    console.log('[CHAIN] klass+0xb0 (static_fields candidate): ' + sf_b0);
                    console.log('[CHAIN] klass+0xb8 (static_fields candidate): ' + sf_b8);

                    // Step 6: Try reading instance pointer from each
                    [['0xb0', sf_b0], ['0xb8', sf_b8]].forEach(function(pair) {
                        var label = pair[0];
                        var sf = pair[1];
                        if (!sf.isNull() && sf.compare(ptr(0x10000000)) > 0) {
                            try {
                                var inst = sf.readPointer();
                                console.log('[CHAIN]   ' + label + ' → static_fields[0] (instance): ' + inst);
                                if (!inst.isNull() && inst.compare(ptr(0x10000000)) > 0) {
                                    var state = inst.add(0x180).readS32();
                                    console.log('[CHAIN]     _m_eState = ' + state + (state === 2 ? ' ✅ THIS IS THE BATTLE MANAGER' : ''));
                                }
                            } catch(e) {
                                console.log('[CHAIN]   ' + label + ' → read error: ' + e);
                            }
                        }
                    });
                }
            } else {
                console.log('[CHAIN] LDR instruction not recognized: 0x' + insn_ldr.toString(16));
            }
        } else {
            console.log('[CHAIN] ADRP instruction not recognized: 0x' + insn_adrp.toString(16));
        }
    } catch(e) {
        console.log('[CHAIN] Error during manual walk: ' + e);
    }

    console.log('\n[*] Hooks active. Enter a match and the hooks will fire automatically.');
    console.log('[*] The manual chain walk above shows what the daemon would resolve.');
}

// Run
setTimeout(main, 0);
