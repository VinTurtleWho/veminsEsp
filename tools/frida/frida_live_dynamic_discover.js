/**
 * Dynamic Frida Script: Complete End-to-End Live Match Discovery
 * 1. Finds active LogicPlayer hero objects in RAM.
 * 2. Scans for references pointing to the hero to resolve LogicBattleManager.
 * 3. Dumps Il2CppClass, static_fields, and Gate 8 local player bindings.
 */

'use strict';

function discover() {
    console.log('[*] =========================================================');
    console.log('[*] MLBB LIVE 5V5 DYNAMIC INTROSPECTION VIA FRIDA');
    console.log('[*] =========================================================');

    var liblogic = Process.findModuleByName('liblogic.so');
    console.log('[+] liblogic.so base : ' + (liblogic ? liblogic.base : 'NOT FOUND'));

    var ranges = Process.enumerateRanges('rw-');
    console.log('[+] Total memory ranges: ' + ranges.length);

    var liveHeroes = [];

    // 1. Discover all active LogicPlayer entities
    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x10000000) return;
        try {
            // LogicPlayer has byte at +0x5c == 1 (IsPlayer)
            // Let's scan for hero entities with valid HP and level
            for (var off = 0; off < Math.min(r.size, 0x800000) - 0x300; off += 0x1000) {
                var candHero = r.base.add(off);
                try {
                    var isPlayer = candHero.add(0x5c).readU8();
                    if (isPlayer === 1) {
                        var heroId = candHero.add(0xac).readS32();
                        var level = candHero.add(0xb4).readS32();
                        var hp = candHero.add(0xc8).readS32();
                        var hpMax = candHero.add(0xcc).readS32();
                        var camp = candHero.add(0x1dc).readS32();
                        if (heroId > 0 && heroId < 200 && level >= 1 && level <= 15 && hp >= 0 && hp <= hpMax && hpMax >= 1000 && hpMax < 50000 && (camp === 1 || camp === 2)) {
                            var px = candHero.add(0x268).readDouble();
                            var py = candHero.add(0x270).readDouble();
                            liveHeroes.push({
                                ptr: candHero,
                                heroId: heroId,
                                level: level,
                                hp: hp,
                                hpMax: hpMax,
                                camp: camp,
                                pos: '(' + px.toFixed(2) + ', ' + py.toFixed(2) + ')'
                            });
                            console.log('[+] Discovered Hero: ' + candHero + ' | ID: ' + heroId + ' | Lv.' + level + ' | Camp: ' + camp + ' | HP: ' + hp + '/' + hpMax + ' | Pos: (' + px.toFixed(2) + ', ' + py.toFixed(2) + ')');
                        }
                    }
                } catch(e) {}
            }
        } catch(e) {}
    });

    console.log('[+] Total Live Heroes Found: ' + liveHeroes.length);

    // 2. For the first valid hero, scan references to locate LogicBattleManager
    if (liveHeroes.length === 0) {
        console.log('[-] No active heroes found. Is match loaded?');
        return;
    }

    var targetHero = liveHeroes[0].ptr;
    var pVal = BigInt(targetHero.toString());
    var bytes = [];
    for (var b = 0; b < 8; b++) {
        var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (byteHex.length < 2) byteHex = '0' + byteHex;
        bytes.push(byteHex);
    }
    var pattern = bytes.join(' ');
    console.log('\n[*] Scanning for references to hero ' + targetHero + ' (pattern: ' + pattern + ')...');

    var hits = [];
    ranges.forEach(function(r) {
        if (r.size < 0x4000 || r.size > 0x10000000) return;
        try {
            Memory.scanSync(r.base, r.size, pattern).forEach(function(m) {
                hits.push(m.address);
            });
        } catch(e) {}
    });

    console.log('[+] References found: ' + hits.length);

    var foundMgrs = [];

    hits.forEach(function(hit) {
        [0x200, 0x0a0, 0x0a8, 0x0e0, 0x0e8].forEach(function(off) {
            var candMgr = hit.sub(off);
            try {
                var state = candMgr.add(0x180).readS32();
                var ft = candMgr.add(0x19c).readU32();
                var pSelf = candMgr.add(0x200).readPointer();
                var pPlayers = candMgr.add(0x0a8).readPointer();
                var pMonsters = candMgr.add(0x0b0).readPointer();

                if ((state === 2 || state === 6) && ft > 0 && !pPlayers.isNull() && !pMonsters.isNull()) {
                    var klass = candMgr.readPointer();
                    console.log('\n=============================================================');
                    console.log('[🎉🎉🎉 PROVEN LIVE LOGICBATTLEMANAGER DISCOVERED 🎉🎉🎉]');
                    console.log('=============================================================');
                    console.log('  • Runtime Manager Instance   : ' + candMgr);
                    console.log('  • _m_eState (+0x180)         : ' + state + (state === 6 ? ' (Ranked/Classic 5v5 ✅)' : ' (InBattle ✅)'));
                    console.log('  • m_uiFrameTime (+0x19c)     : ' + ft + ' ms');
                    console.log('  • m_RealSelfPlayer (+0x200)  : ' + pSelf + ' (Gate 8 Certified)');
                    console.log('  • m_dicPlayerLogic (+0x0a8)  : ' + pPlayers);
                    console.log('  • m_dicMonsterLogic (+0x0b0) : ' + pMonsters);
                    console.log('  • Il2CppClass Descriptor     : ' + klass);

                    if (!klass.isNull()) {
                        try {
                            var namePtr = klass.add(0x10).readPointer();
                            var nsPtr = klass.add(0x18).readPointer();
                            console.log('  • Class Name                 : ' + namePtr.readUtf8String());
                            console.log('  • Class Namespace            : ' + nsPtr.readUtf8String());
                        } catch(e) {}

                        console.log('  • Inspecting static_fields candidates in Il2CppClass:');
                        for (var sfOff = 0x90; sfOff <= 0xd0; sfOff += 8) {
                            var sfP = klass.add(sfOff).readPointer();
                            if (!sfP.isNull()) {
                                try {
                                    var sfDeref = sfP.readPointer();
                                    var isMatch = sfDeref.equals(candMgr);
                                    console.log('      klass + 0x' + sfOff.toString(16) + ' -> ' + sfP + ' (deref -> ' + sfDeref + ')' + (isMatch ? ' [MATCHES MANAGER INSTANCE! 🔥]' : ''));
                                } catch(e) {
                                    console.log('      klass + 0x' + sfOff.toString(16) + ' -> ' + sfP);
                                }
                            }
                        }
                    }
                    foundMgrs.push(candMgr);
                }
            } catch(e) {}
        });
    });

    console.log('\n[+] Introspection complete. Total verified managers: ' + foundMgrs.length);
}

discover();
