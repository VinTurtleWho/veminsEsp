/**
 * Production Lobby-to-Match Frida Hook
 * Arms hooks while in lobby and captures full LogicBattleManager topology on entry.
 */

'use strict';

function armLobbyHook() {
    console.log('[*] =========================================================');
    console.log('[*] MLBB ARMED HOOK (LOBBY -> 5V5 MATCH ENTRY)');
    console.log('[*] =========================================================');

    var liblogic = Process.findModuleByName('liblogic.so');
    if (!liblogic) {
        console.log('[-] liblogic.so not found yet! Retrying in 2 seconds...');
        setTimeout(armLobbyHook, 2000);
        return;
    }

    console.log('[+] Target Module: liblogic.so @ ' + liblogic.base + ' (size: ' + liblogic.size + ')');

    var rva_getLocal = ptr('0x1648e7c');
    var targetAddr = liblogic.base.add(rva_getLocal);
    console.log('[+] Target Method: LogicBattleManager.get_m_LocalPlayerLogic @ ' + targetAddr + ' (RVA 0x1648e7c)');

    var capturedInstances = {};
    var hitCount = 0;

    try {
        Interceptor.attach(targetAddr, {
            onEnter: function(args) {
                hitCount++;
                var mgr = this.context.x0;
                var mgrKey = mgr.toString();

                // Only perform deep dump once per unique instance or every 100 hits
                if (capturedInstances[mgrKey] && (hitCount % 120 !== 0)) {
                    return;
                }
                capturedInstances[mgrKey] = true;

                console.log('\n[🔥 LIVE HOOK TRIGGERED (Hit #' + hitCount + ') 🔥]');
                console.log('[+] LogicBattleManager Instance Address: ' + mgr);

                try {
                    // 1. Read class descriptor from object header (+0x00)
                    var klass = mgr.readPointer();
                    console.log('[+] Manager Il2CppClass Descriptor     : ' + klass);

                    if (!klass.isNull()) {
                        var namePtr = klass.add(0x10).readPointer();
                        var nsPtr = klass.add(0x18).readPointer();
                        var cname = !namePtr.isNull() ? namePtr.readUtf8String() : 'null';
                        var cns = !nsPtr.isNull() ? nsPtr.readUtf8String() : 'null';
                        console.log('[+] Class Identity                     : ' + (cns ? cns + '.' : '') + cname);

                        // 2. Scan Il2CppClass fields for static_fields table (+0x90 to +0xd0)
                        console.log('[+] Il2CppClass static fields table:');
                        for (var off = 0x90; off <= 0xd0; off += 8) {
                            var sfVal = klass.add(off).readPointer();
                            if (!sfVal.isNull()) {
                                try {
                                    var sfDeref = sfVal.readPointer();
                                    var isSelf = sfDeref.equals(mgr);
                                    console.log('    klass + 0x' + off.toString(16) + ' -> ' + sfVal + ' (deref -> ' + sfDeref + ')' + (isSelf ? ' [MATCHES SINGLETON INSTANCE! 🎯]' : ''));
                                } catch(e) {
                                    console.log('    klass + 0x' + off.toString(16) + ' -> ' + sfVal);
                                }
                            }
                        }
                    }

                    // 3. Read Manager Core State
                    var state = mgr.add(0x180).readS32();
                    var frameTime = mgr.add(0x19c).readU32();
                    var selfPlayer = mgr.add(0x200).readPointer();
                    var localPlayer = mgr.add(0x0a0).readPointer();
                    var dicPlayer = mgr.add(0x0a8).readPointer();
                    var dicMonster = mgr.add(0x0b0).readPointer();
                    var campAList = mgr.add(0x0e0).readPointer();
                    var campBList = mgr.add(0x0e8).readPointer();
                    var soldierList = mgr.add(0x128).readPointer();

                    console.log('[+] _m_eState (+0x180)                 : ' + state + (state === 2 ? ' (IN_BATTLE ✅)' : ' (Lobby/Loading)'));
                    console.log('[+] m_uiFrameTime (+0x19c)             : ' + frameTime);
                    console.log('[+] m_RealSelfPlayer (+0x200)          : ' + selfPlayer);
                    console.log('[+] m_LocalPlayerLogic (+0x0a0)        : ' + localPlayer);
                    console.log('[+] m_dicPlayerLogic (+0x0a8)          : ' + dicPlayer);
                    console.log('[+] m_dicMonsterLogic (+0x0b0)         : ' + dicMonster);
                    console.log('[+] m_CampAList (+0x0e0)               : ' + campAList);
                    console.log('[+] m_CampBList (+0x0e8)               : ' + campBList);
                    console.log('[+] m_SoldierList (+0x128)             : ' + soldierList);

                    // 4. Verify Local Player via Gate 8 (+0x200)
                    var targetHero = !selfPlayer.isNull() ? selfPlayer : localPlayer;
                    if (!targetHero.isNull()) {
                        var isPlayer = targetHero.add(0x5c).readU8();
                        var heroId = targetHero.add(0xac).readS32();
                        var level = targetHero.add(0xb4).readS32();
                        var hp = targetHero.add(0xc8).readS32();
                        var hpMax = targetHero.add(0xcc).readS32();
                        var posX = targetHero.add(0x268).readDouble();
                        var posY = targetHero.add(0x270).readDouble();
                        var camp = targetHero.add(0x1dc).readS32();
                        var isDead = targetHero.add(0x1d0).readU8();

                        console.log('    ----------------------------------------');
                        console.log('    [GATE 8 LOCAL HERO VERIFICATION]');
                        console.log('    ----------------------------------------');
                        console.log('    IsPlayer (+0x5c)  : ' + isPlayer + (isPlayer === 1 ? ' (PROVEN)' : ' (INVALID)'));
                        console.log('    Hero ID (+0xac)   : ' + heroId);
                        console.log('    Level (+0xb4)     : ' + level);
                        console.log('    HP (+0xc8/+0xcc)  : ' + hp + ' / ' + hpMax);
                        console.log('    Position (X, Y)   : (' + posX.toFixed(2) + ', ' + posY.toFixed(2) + ')');
                        console.log('    Camp (+0x1dc)     : ' + camp + (camp === 1 ? ' (Camp A)' : camp === 2 ? ' (Camp B)' : ''));
                        console.log('    IsDead (+0x1d0)   : ' + isDead);
                    }

                    // 5. Ingest Player Dictionary (5v5 participants)
                    if (!dicPlayer.isNull()) {
                        var entriesPtr = dicPlayer.add(0x18).readPointer();
                        var count = dicPlayer.add(0x20).readS32();
                        console.log('    ----------------------------------------');
                        console.log('    [5V5 PLAYER DICTIONARY INGESTION]');
                        console.log('    ----------------------------------------');
                        console.log('    Active Players Count : ' + count);
                        console.log('    Entries Array Ptr    : ' + entriesPtr);

                        if (!entriesPtr.isNull() && count > 0 && count <= 20) {
                            for (var p = 0; p < count; p++) {
                                var entryOff = 0x20 + (p * 24);
                                var hashCode = entriesPtr.add(entryOff).readS32();
                                var key = entriesPtr.add(entryOff + 0x08).readU64();
                                var valPtr = entriesPtr.add(entryOff + 0x10).readPointer();
                                if (hashCode >= 0 && !valPtr.isNull()) {
                                    try {
                                        var pHeroId = valPtr.add(0xac).readS32();
                                        var pLvl = valPtr.add(0xb4).readS32();
                                        var pHp = valPtr.add(0xc8).readS32();
                                        var pCamp = valPtr.add(0x1dc).readS32();
                                        console.log('      [Player #' + (p + 1) + '] Key=' + key + ' | Addr=' + valPtr + ' | HeroID=' + pHeroId + ' | Lvl=' + pLvl + ' | HP=' + pHp + ' | Camp=' + pCamp);
                                    } catch(e) {
                                        console.log('      [Player #' + (p + 1) + '] Key=' + key + ' | Addr=' + valPtr);
                                    }
                                }
                            }
                        }
                    }

                } catch(e) {
                    console.log('[-] Inspection error: ' + e);
                }
            }
        });

        console.log('[+] Interceptor successfully attached to get_m_LocalPlayerLogic!');
        console.log('[+] System is armed and listening. You can now start matchmaking and enter the match.');
    } catch(e) {
        console.log('[-] Interceptor attach failed: ' + e);
    }
}

setTimeout(armLobbyHook, 100);
