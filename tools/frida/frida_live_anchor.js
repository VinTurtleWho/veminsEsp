/**
 * Fast Anchor-Pointer Discovery in Live Memory via Frida
 * Scans memory for references to the live LogicPlayer pointer,
 * and validates the containing LogicBattleManager object and its Il2CppClass!
 */

'use strict';

function scanAnchor() {
    console.log('[*] =========================================================');
    console.log('[*] LIVE HERO ANCHOR SCAN & BATTLEMANAGER DISCOVERY');
    console.log('[*] =========================================================');

    var liblogic = Process.findModuleByName('liblogic.so');
    console.log('[+] liblogic.so base: ' + liblogic.base);

    // We can dynamically scan for LogicPlayer objects or use pattern
    // Let's enumerate heap memory ranges (rw-)
    var ranges = Process.enumerateRanges('rw-');
    console.log('[+] Scannable memory ranges (rw-): ' + ranges.length);

    // First find any LogicPlayer instances by looking for IsPlayer == 1 at +0x5c
    // Or scan for objects with VTable signature
    var candidatePlayers = [];

    // Let's do a fast scan across rw ranges for BattleManager candidates
    // A LogicBattleManager candidate has:
    // 1. _m_eState (+0x180) == 2 (int32 0x00000002)
    // 1. _m_eState (+0x180) == 2 or 6
    // 2. m_uiFrameTime (+0x19c) > 100
    // 3. m_RealSelfPlayer (+0x200) is a valid heap pointer with IsPlayer (+0x5c) == 1
    // 4. m_dicPlayerLogic (+0x0a8) is a valid pointer

    var foundManagers = [];

    var patterns = ['02 00 00 00', '06 00 00 00'];

    patterns.forEach(function(pat) {
        var stateVal = pat.startsWith('02') ? 2 : 6;
        ranges.forEach(function(range) {
            if (range.size < 0x1000 || range.size > 0x10000000) return;

            try {
                Memory.scan(range.base, range.size, pat, {
                    onMatch: function(matchAddr, size) {
                        // matchAddr is a candidate for _m_eState (+0x180)
                        var mgrCandidate = matchAddr.sub(0x180);

                        try {
                            // Check frame time at +0x19c
                            var ft = mgrCandidate.add(0x19c).readU32();
                            if (ft < 10 || ft > 100000000) return;

                            // Check m_RealSelfPlayer at +0x200 or m_LocalPlayerLogic at +0x0a0
                            var selfP = mgrCandidate.add(0x200).readPointer();
                            var localP = mgrCandidate.add(0x0a0).readPointer();
                            var dicP = mgrCandidate.add(0x0a8).readPointer();

                            var heroP = !selfP.isNull() ? selfP : localP;
                            if (heroP.isNull() || dicP.isNull()) return;

                            // Check IsPlayer at hero + 0x5c
                            var isPlayer = heroP.add(0x5c).readU8();
                            if (isPlayer !== 1) return;

                            // Check hero level (1..15) and HP
                            var level = heroP.add(0xb4).readS32();
                            var hp = heroP.add(0xc8).readS32();
                            var hpMax = heroP.add(0xcc).readS32();
                            if (level < 1 || level > 15 || hpMax < 100 || hp > hpMax || hp < 0) return;

                            // Found a proven candidate!
                            var klass = mgrCandidate.readPointer();
                            console.log('\n[🎉 PROVEN LOGICBATTLEMANAGER FOUND 🎉]');
                            console.log('[+] Manager Instance Address : ' + mgrCandidate);
                            console.log('[+] Manager Il2CppClass      : ' + klass);
                            console.log('[+] _m_eState (+0x180)       : ' + stateVal);
                            console.log('[+] m_uiFrameTime (+0x19c)   : ' + ft);
                            console.log('[+] m_RealSelfPlayer (+0x200): ' + selfP);
                            console.log('[+] m_LocalPlayerLogic (+0xa0): ' + localP);
                            console.log('[+] m_dicPlayerLogic (+0xa8) : ' + dicP);
                            console.log('[+] Hero Level               : ' + level);
                            console.log('[+] Hero HP                  : ' + hp + ' / ' + hpMax);
                            console.log('[+] Hero Position (X, Y)     : ' + heroP.add(0x268).readDouble().toFixed(2) + ', ' + heroP.add(0x270).readDouble().toFixed(2));
                            console.log('[+] Hero Camp (+0x1dc)       : ' + heroP.add(0x1dc).readS32());

                            // Inspect klass structure and find static_fields
                            if (!klass.isNull()) {
                                var namePtr = klass.add(0x10).readPointer();
                                var nsPtr = klass.add(0x18).readPointer();
                                try {
                                    console.log('[+] Class Name               : ' + namePtr.readUtf8String());
                                    console.log('[+] Class Namespace          : ' + nsPtr.readUtf8String());
                                } catch(e) {}

                                // Check all fields around +0x90 to +0xd0 in klass
                                console.log('[+] Il2CppClass static_fields candidates:');
                                for (var off = 0x90; off <= 0xd0; off += 8) {
                                    var sfVal = klass.add(off).readPointer();
                                    if (!sfVal.isNull()) {
                                        try {
                                            var sfInst = sfVal.readPointer();
                                            var isMatch = sfInst.equals(mgrCandidate);
                                            console.log('    klass + 0x' + off.toString(16) + ' -> ' + sfVal + ' (deref -> ' + sfInst + ')' + (isMatch ? ' [MATCHES MANAGER INSTANCE! 🔥]' : ''));
                                        } catch(e) {}
                                    }
                                }
                            }

                            foundManagers.push(mgrCandidate);
                        } catch(e) {}
                    },
                    onError: function(reason) {},
                    onComplete: function() {}
                });
            } catch(e) {}
        });
    });

    console.log('\n[+] Scan finished. Total BattleManagers discovered: ' + foundManagers.length);
}

scanAnchor();
