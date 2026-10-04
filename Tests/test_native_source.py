from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class NativeSourceTests(unittest.TestCase):
    def test_no_lua_transport_or_duplicate_region_ownership(self):
        facade=(ROOT/'Adapters/Sunrise/frontier_probe.h').read_text(encoding='utf-8')
        self.assertIn('legacy_status(target,connected,live)',facade)
        self.assertNotIn('CreateFileMapping',facade);self.assertNotIn('++sequence',facade)
        native=(ROOT/'Native/frontier_native.cpp').read_text(encoding='utf-8')
        self.assertIn('sequence.compare_exchange_weak',native)
        self.assertIn('now-lastPoll>=100',native)
        self.assertNotIn('lua_State',native);self.assertNotIn('CreateThread',native)
    def test_override_cannot_leak_through_persistent_toggle(self):
        patch=(ROOT/'Native/Sunrise.patch').read_text(encoding='utf-8')
        self.assertIn('Settings runtime_get() noexcept',patch)
        self.assertIn('GetTickCount64() < g_frontierHoverUntil',patch)
        # Override is applied only to the returned copy; the persistent get remains unchanged.
        self.assertIn('if (g_frontierHoverUntil && GetTickCount64() < g_frontierHoverUntil) snapshot.flyEnabled = true;',patch)
        self.assertNotIn('+    g_settings.flyEnabled',patch)
    def test_all_native_mapping_names_match_python_exactly(self):
        import re
        import sys
        sys.path.insert(0,str(ROOT/'Core'))
        from frontier.ipc import NAME as bridge
        from frontier.spatial import NAME as spatial
        from frontier.control import NAME as control
        protocol=(ROOT/'Native/frontier_protocol.h').read_text(encoding='utf-8')
        actual=dict(re.findall(r'constexpr wchar_t (\w+)\[\]=LR"\(([^)]*)\)";',protocol))
        self.assertEqual(actual,dict(bridgeName=bridge,bridgeMutex=bridge+'_mutex',spatialName=spatial,spatialMutex=spatial+'_mutex',controlName=control,controlMutex=control+'_mutex'))
        native=(ROOT/'Native/frontier_native.cpp').read_text(encoding='utf-8')
        self.assertNotIn('L"Local',native)
        for name in actual:self.assertIn(name,native)

    def test_readiness_uses_published_snapshot_not_same_frame_body(self):
        native=(ROOT/'Native/frontier_native.cpp').read_text(encoding='utf-8')
        self.assertIn('const auto playerSnapshot=player::position::snapshot();',native)
        self.assertIn('const auto position=playerSnapshot.position;',native)
        self.assertIn('const bool inWorld=hooks::bootflow::in_world();',native)
        self.assertIn('guardian_readiness_bits(inWorld,component!=nullptr,ownsLocal,playerSnapshot)',native)
        self.assertIn('const bool ownsLocal=inWorld&&component&&hooks::teleport::owns_local_player(component);',native)
        self.assertIn('poll_spatial(now,ready,position)',native)
        self.assertNotIn('read_position(',native)

    def test_diagnostics_are_native_owned_and_transition_only(self):
        native=(ROOT/'Native/frontier_native.cpp').read_text(encoding='utf-8')
        self.assertIn('result.readinessBits=readinessBits;',native)
        self.assertIn('if(readinessTransitions.observe(readinessBits))',native)
        self.assertIn('ev=frontier_readiness',native)
        self.assertIn('policy.tick(command,now,incarnation,ready&&hostReady,',native)
        protocol=(ROOT/'Native/frontier_protocol.h').read_text(encoding='utf-8')
        self.assertIn('offsetof(ControlBlock,readinessBits)==108',protocol)

    def test_locomotion_uses_authored_polled_keys_and_actual_snapshot_delta(self):
        native=(ROOT/'Native/frontier_native.cpp').read_text()
        patch=(ROOT/'Native/Sunrise.patch').read_text()
        motion=(ROOT/'Native/frontier_motion.h').read_text()
        self.assertIn('hooks::teleport::action_key(code)',native)
        self.assertIn('account.settings.keyBindings.values',native)
        self.assertIn('!policy.hovering&&!movement::get().flyEnabled',native)
        self.assertIn('motionAccumulator.sample(',native)
        self.assertIn('position[0]-previous[0]',motion)
        self.assertIn('frontier::motion_key(',patch)
        for forbidden in ('SendInput','SetForegroundWindow','WriteProcessMemory','CreateThread'):
            self.assertNotIn(forbidden,native)
        self.assertNotIn('edz_freeroam',native)
