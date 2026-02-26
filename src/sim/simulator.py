import random
import asyncio
from typing import TYPE_CHECKING

from src.systems.time import Month, Year, MonthStamp
from src.classes.core.avatar import Avatar, Gender
from src.sim.avatar_awake import process_awakening
from src.classes.age import Age
from src.systems.cultivation import Realm
from src.classes.core.world import World
from src.classes.event import Event, is_null_event
from src.classes.ai import llm_ai
from src.utils.name_generator import get_random_name
from src.utils.config import CONFIG
from src.run.log import get_logger
from src.systems.fortune import try_trigger_fortune
from src.systems.fortune import try_trigger_misfortune
from src.classes.celestial_phenomenon import get_random_celestial_phenomenon
from src.classes.long_term_objective import process_avatar_long_term_objective
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.i18n import t
from src.classes.observe import get_avatar_observation_radius
from src.classes.environment.region import CultivateRegion, CityRegion
from src.classes.birth import process_births
from src.classes.nickname import process_avatar_nickname
from src.classes.relation.relation_resolver import RelationResolver
from src.classes.relation.relations import update_second_degree_relations

class Simulator:
    def __init__(self, world: World):
        self.world = world
        self.awakening_rate = CONFIG.game.npc_awakening_rate_per_month  # Đọc tỉ lệ giác thức NPC mỗi tháng từ config (thường dân → tu sĩ)

    def _phase_update_perception_and_knowledge(self, living_avatars: list[Avatar]):
        """
        Giai đoạn cập nhật nhận thức:
        1. Cập nhật known_regions dựa trên phạm vi quan sát
        2. Tự động chiếm đóng động phủ vô chủ (nếu bản thân chưa có động phủ)
        """
        events = []
        # 1. Cache danh sách ID các nhân vật đã có động phủ
        avatars_with_home = set()
        # ...
        cultivate_regions = [
            r for r in self.world.map.regions.values() 
            if isinstance(r, CultivateRegion)
        ]
        
        for r in cultivate_regions:
            if r.host_avatar:
                avatars_with_home.add(r.host_avatar.id)

        # 2. Duyệt qua toàn bộ nhân vật còn sống
        for avatar in living_avatars:
            # ...
            # Tính bán kính quan sát (khoảng cách Manhattan)
            radius = get_avatar_observation_radius(avatar)
            
            # ...
            # Lấy tọa độ hợp lệ trong phạm vi quan sát
            start_x = max(0, avatar.pos_x - radius)
            end_x = min(self.world.map.width - 1, avatar.pos_x + radius)
            start_y = max(0, avatar.pos_y - radius)
            end_y = min(self.world.map.height - 1, avatar.pos_y + radius)

            # Thu thập các khu vực quan sát được
            observed_regions = set()
            for x in range(start_x, end_x + 1):
                for y in range(start_y, end_y + 1):
                    # Kiểm tra khoảng cách: dùng khoảng cách Manhattan
                    if abs(x - avatar.pos_x) + abs(y - avatar.pos_y) <= radius:
                        tile = self.world.map.get_tile(x, y)
                        if tile.region:
                            observed_regions.add(tile.region)

            # Cập nhật nhận thức và tự động chiếm đóng
            for region in observed_regions:
                # Cập nhật known_regions (danh sách khu vực đã biết)
                avatar.known_regions.add(region.id)
                
                # Logic tự động chiếm đóng động phủ
                # Chỉ kích hoạt khi: là khu tu luyện + không có chủ + bản thân chưa có động phủ
                if isinstance(region, CultivateRegion):
                    if region.host_avatar is None:
                        if avatar.id not in avatars_with_home:
                            # Chiếm đóng
                            avatar.occupy_region(region)
                            avatars_with_home.add(avatar.id)
                            # Ghi lại sự kiện
                            event = Event(
                                self.world.month_stamp,
                                t("{avatar_name} passed by {region_name}, found it ownerless, and occupied it.", 
                                  avatar_name=avatar.name, region_name=region.name),
                                related_avatars=[avatar.id]
                            )
                            events.append(event)
        return events

    async def _phase_decide_actions(self, living_avatars: list[Avatar]):
        """
        Giai đoạn ra quyết định: chỉ gọi AI cho các nhân vật cần kế hoạch mới
        (hiện không có hành động và không có kế hoạch),
        nạp kết quả quyết định của AI thành chuỗi kế hoạch của nhân vật.
        """
        avatars_to_decide = []
        for avatar in living_avatars:
            if avatar.current_action is None and not avatar.has_plans():
                avatars_to_decide.append(avatar)
        if not avatars_to_decide:
            return
        ai = llm_ai
        decide_results = await ai.decide(self.world, avatars_to_decide)
        for avatar, result in decide_results.items():
            action_name_params_pairs, avatar_thinking, short_term_objective, _event = result
            # Chỉ đưa vào hàng đợi kế hoạch, không thêm sự kiện bắt đầu ở đây
            # để tránh trùng lặp với giai đoạn commit
            avatar.load_decide_result_chain(action_name_params_pairs, avatar_thinking, short_term_objective)

    def _phase_commit_next_plans(self, living_avatars: list[Avatar]):
        """
        Giai đoạn commit: cho các nhân vật rảnh rỗi commit hành động tiếp theo
        trong kế hoạch, trả về tập hợp sự kiện bắt đầu.
        """
        events = []
        for avatar in living_avatars:
            if avatar.current_action is None:
                start_event = avatar.commit_next_plan()
                if start_event is not None and not is_null_event(start_event):
                    events.append(start_event)
        return events

    async def _phase_execute_actions(self, living_avatars: list[Avatar]):
        """
        Giai đoạn thực thi: tiến hành hành động hiện tại, hỗ trợ kết toán
        chuỗi chiếm quyền trong cùng tháng, trả về các sự kiện phát sinh.
        """
        events = []
        MAX_LOCAL_ROUNDS = CONFIG.game.max_action_rounds_per_turn
        
        # Round 1: Toàn bộ nhân vật thực thi một lần
        avatars_needing_retry = set()
        for avatar in living_avatars:
            try:
                new_events = await avatar.tick_action()
                if new_events:
                    events.extend(new_events)
                
                # Kiểm tra xem có hành động mới phát sinh không (chiếm quyền/combo),
                # nếu có thì đưa vào round tiếp theo.
                # Lưu ý: tick_action đã xử lý logic xóa cờ bên trong,
                # chỉ giữ True khi thực sự có chuyển đổi hành động
                if getattr(avatar, "_new_action_set_this_step", False):
                    avatars_needing_retry.add(avatar)
            except Exception as e:
                # Ghi log lỗi chi tiết
                get_logger().logger.error(f"Avatar {avatar.name}({avatar.id}) tick_action failed: {e}", exc_info=True)
                # Đảm bảo không vào logic retry
                if hasattr(avatar, "_new_action_set_this_step"):
                     avatar._new_action_set_this_step = False

        # Round 2+: Chỉ thực thi các nhân vật có hành động mới,
        # tránh các nhân vật vô can bị thực thi lại
        round_count = 1
        while avatars_needing_retry and round_count < MAX_LOCAL_ROUNDS:
            current_avatars = list(avatars_needing_retry)
            avatars_needing_retry.clear()
            
            for avatar in current_avatars:
                try:
                    new_events = await avatar.tick_action()
                    if new_events:
                        events.extend(new_events)
                    
                    # Kiểm tra lại
                    if getattr(avatar, "_new_action_set_this_step", False):
                        avatars_needing_retry.add(avatar)
                except Exception as e:
                    get_logger().logger.error(f"Avatar {avatar.name}({avatar.id}) retry tick_action failed: {e}", exc_info=True)
                    if hasattr(avatar, "_new_action_set_this_step"):
                        avatar._new_action_set_this_step = False
            
            round_count += 1
            
        return events

    def _phase_resolve_death(self, living_avatars: list[Avatar]):
        """
        Kết toán tử vong:
        - Tử vong do chiến đấu đã được xử lý bên trong Action
        - Lúc này các avatar còn lại đều đang sống, chỉ cần kiểm tra
          nguyên nhân phi chiến đấu (ví dụ: lão tử, mất máu bị động)

        Lưu ý: Nếu phát hiện tử vong, sẽ xóa khỏi danh sách living_avatars
        được truyền vào, tránh các giai đoạn sau tiếp tục xử lý.
        """
        events = []
        dead_avatars = []
        
        for avatar in living_avatars:
            is_dead = False
            death_reason: DeathReason | None = None
            
            # Ưu tiên kiểm tra trọng thương trước (có thể do hiệu ứng bị động gây ra)
            if avatar.hp.cur <= 0:
                is_dead = True
                death_reason = DeathReason(DeathType.SERIOUS_INJURY)
            # Sau đó kiểm tra thọ nguyên
            elif avatar.death_by_old_age():
                is_dead = True
                death_reason = DeathReason(DeathType.OLD_AGE)
                
            if is_dead and death_reason:
                event = Event(self.world.month_stamp, f"{avatar.name}{death_reason}", related_avatars=[avatar.id])
                events.append(event)
                handle_death(self.world, avatar, death_reason)
                dead_avatars.append(avatar)
        
        # Xóa khỏi danh sách tham chiếu hiện tại,
        # đảm bảo các Phase sau không xử lý nhân vật đã chết
        for dead in dead_avatars:
            if dead in living_avatars:
                living_avatars.remove(dead)
                
        return events

    def _phase_update_age_and_birth(self, living_avatars: list[Avatar]):
        """
        Cập nhật tuổi tác của các nhân vật còn sống, đồng thời với xác suất
        nhất định tạo ra tu sĩ mới, trả về tập hợp sự kiện phát sinh.
        """
        events = []
        for avatar in living_avatars:
            avatar.update_age(self.world.month_stamp)
            
        # 1. Quản lý thường dân: dọn dẹp thường dân già chết
        self.world.mortal_manager.cleanup_dead_mortals(self.world.month_stamp)
        
        # 2. Giác thức thường dân (huyết mạch + tự nhiên)
        awakening_events = process_awakening(self.world)
        if awakening_events:
            events.extend(awakening_events)
            
        # 3. Đạo lữ sinh con
        birth_events = process_births(self.world)
        if birth_events:
            events.extend(birth_events)
            
        return events

    async def _phase_passive_effects(self, living_avatars: list[Avatar]):
        """
        Giai đoạn kết toán bị động:
        - Xử lý đan dược hết hạn
        - Cập nhật hiệu ứng theo thời gian (ví dụ: hồi HP)
        - Kích hoạt kỳ ngộ (không phải từ hành động)
        """
        events = []
        for avatar in living_avatars:
            # 1. Xử lý đan dược hết hạn
            avatar.process_elixir_expiration(int(self.world.month_stamp))
            # 2. Cập nhật hiệu ứng bị động (ví dụ: hồi HP theo thời gian)
            avatar.update_time_effect()
        
        # Dùng gather để kích hoạt kỳ ngộ và vận hạn song song (async concurrent)
        tasks_fortune = [try_trigger_fortune(avatar) for avatar in living_avatars]
        tasks_misfortune = [try_trigger_misfortune(avatar) for avatar in living_avatars]
        results = await asyncio.gather(*(tasks_fortune + tasks_misfortune))
        
        events.extend([e for res in results if res for e in res])
                
        return events
    
    async def _phase_nickname_generation(self, living_avatars: list[Avatar]):
        """
        Giai đoạn sinh biệt hiệu (nickname)
        """
        # Thực thi đồng thời (concurrent)
        tasks = [process_avatar_nickname(avatar) for avatar in living_avatars]
        results = await asyncio.gather(*tasks)
        
        events = [e for e in results if e]
        return events
    
    async def _phase_long_term_objective_thinking(self, living_avatars: list[Avatar]):
        """
        Giai đoạn suy nghĩ mục tiêu dài hạn.
        Kiểm tra xem nhân vật có cần sinh mới / cập nhật mục tiêu dài hạn không.
        """
        # Thực thi đồng thời (concurrent)
        tasks = [process_avatar_long_term_objective(avatar) for avatar in living_avatars]
        results = await asyncio.gather(*tasks)
        
        events = [e for e in results if e]
        return events
    
    async def _phase_process_gatherings(self):
        """
        Giai đoạn kết toán Gathering:
        Kiểm tra và thực thi các sự kiện tập hợp nhiều người đã đăng ký
        (ví dụ: phiên đấu giá, tỷ võ đại hội...).
        """
        # Năm đầu tiên không kích hoạt sự kiện tập hợp, cho thời gian phát triển ban đầu
        if self.world.month_stamp.get_year() <= self.world.start_year:
            return []

        return await self.world.gathering_manager.check_and_run_all(self.world)
    
    def _phase_update_celestial_phenomenon(self):
        """
        Cập nhật thiên địa linh cơ (Celestial Phenomenon):
        - Kiểm tra thiên tượng hiện tại có hết hạn chưa
        - Nếu hết hạn → chọn ngẫu nhiên thiên tượng mới
        - Sinh sự kiện thế giới ghi lại sự thay đổi thiên tượng

        Thời điểm thay đổi thiên tượng:
        - Năm khởi tạo (ví dụ năm 100): tháng 1 bắt đầu thiên tượng đầu tiên ngay
        - Cứ sau N năm (thời gian tồn tại của thiên tượng hiện tại) thì thay đổi một lần
        """
        events = []
        current_year = self.world.month_stamp.get_year()
        current_month = self.world.month_stamp.get_month()
        
        # Kiểm tra xem có cần khởi tạo hoặc cập nhật thiên tượng không:
        # 1. Nếu chưa có thiên tượng nào (khởi tạo lần đầu)
        # 2. Nếu đã có và đến hạn (kiểm tra vào tháng 1 mỗi năm)
        should_update = False
        is_init = False
        
        if self.world.current_phenomenon is None:
            should_update = True
            is_init = True
        elif current_month == Month.JANUARY:
            elapsed_years = current_year - self.world.phenomenon_start_year
            if elapsed_years >= self.world.current_phenomenon.duration_years:
                should_update = True

        if should_update:
            old_phenomenon = self.world.current_phenomenon
            new_phenomenon = get_random_celestial_phenomenon()
            
            if new_phenomenon:
                self.world.current_phenomenon = new_phenomenon
                self.world.phenomenon_start_year = current_year
                
                desc = ""
                if is_init:
                    desc = t("world_creation_phenomenon", name=new_phenomenon.name, desc=new_phenomenon.desc)
                else:
                    desc = t("phenomenon_change", old_name=old_phenomenon.name, new_name=new_phenomenon.name, new_desc=new_phenomenon.desc)
                
                event = Event(
                    self.world.month_stamp,
                    desc,
                    related_avatars=None
                )
                events.append(event)
        
        return events

    def _phase_update_region_prosperity(self):
        """
        Phục hồi tự nhiên độ phồn vinh thành phố mỗi tháng
        """
        for region in self.world.map.regions.values():
            if isinstance(region, CityRegion):
                region.change_prosperity(1)

    def _phase_log_events(self, events):
        """
        Ghi các sự kiện vào log.
        """
        logger = get_logger().logger
        for event in events:
            logger.info("EVENT: %s", str(event))

    def _phase_process_interactions(self, events: list[Event]):
        """
        Xử lý logic tương tác trong các sự kiện:
        Duyệt tất cả sự kiện, nếu sự kiện liên quan đến nhiều nhân vật,
        tự động cập nhật bộ đếm tương tác giữa các nhân vật đó.
        """
        for event in events:
            if not event.related_avatars or len(event.related_avatars) < 2:
                continue
            
            # Chỉ tính là tương tác khi sự kiện liên quan đến >= 2 nhân vật
            for aid in event.related_avatars:
                avatar = self.world.avatar_manager.get_avatar(aid)
                if avatar:
                    avatar.process_interaction_from_event(event)

    def _phase_handle_interactions(self, events: list[Event], processed_ids: set[str]):
        """
        Trích xuất các sự kiện tương tác chưa được xử lý từ danh sách sự kiện
        và cập nhật bộ đếm tương tác.
        """
        new_interactions = []
        for e in events:
            if e.id not in processed_ids:
                if e.related_avatars and len(e.related_avatars) >= 2:
                    new_interactions.append(e)
                processed_ids.add(e.id)
        
        if new_interactions:
            self._phase_process_interactions(new_interactions)

    async def _phase_evolve_relations(self, living_avatars: list[Avatar]):
        """
        Giai đoạn tiến hóa quan hệ: kiểm tra và xử lý các thay đổi
        quan hệ nhân vật thỏa mãn điều kiện.
        """
        pairs_to_resolve = []
        processed_pairs = set() # (id1, id2) với id1 < id2
        
        for avatar in living_avatars:
            target_ids = list(avatar.relation_interaction_states.keys())
            
            for target_id in target_ids:
                state = avatar.relation_interaction_states[target_id]
                target = self.world.avatar_manager.get_avatar(target_id)
                
                if target is None or target.is_dead:
                    continue

                # Kiểm tra xem có đủ điều kiện kích hoạt không
                threshold = CONFIG.social.relation_check_threshold
                if state["count"] >= threshold:
                    # Đảm bảo tính duy nhất của cặp
                    id1, id2 = sorted([str(avatar.id), str(target.id)])
                    pair_key = (id1, id2)
                    
                    if pair_key not in processed_pairs:
                        processed_pairs.add(pair_key)
                        pairs_to_resolve.append((avatar, target))
                        
                        # Reset bộ đếm của cả hai bên để tránh kích hoạt lại
                        # 1. Reset bên A
                        state["count"] = 0
                        state["checked_times"] += 1
                        
                        # 2. Reset bên B
                        t_state = target.relation_interaction_states[str(avatar.id)]
                        t_state["count"] = 0
                        t_state["checked_times"] += 1
        
        events = []
        if pairs_to_resolve:
            # Xử lý đồng thời theo batch và thu thập sự kiện trả về
            relation_events = await RelationResolver.run_batch(pairs_to_resolve)
            if relation_events:
                events.extend(relation_events)
            
        return events

    async def step(self):
        """
        Tiến một bước thời gian (một tháng):
        1.  Cập nhật cảm quan & vùng đã biết (và tự động chiếm động phủ)
        2.  Suy nghĩ mục tiêu dài hạn
        3.  Kết toán Gathering (sự kiện tập hợp nhiều người)
        4.  Giai đoạn ra quyết định (AI chọn hành động)
        5.  Giai đoạn commit (bắt đầu thực hiện hành động)
        6.  Giai đoạn thực thi (tick hành động)
        7.  Xử lý bộ đếm tương tác ban đầu (cho tiến hóa quan hệ sau)
        8.  Giai đoạn tiến hóa quan hệ
        9.  Kết toán tử vong
        10. Tuổi tác và sinh mới
        11. Kết toán bị động (đan dược, hiệu ứng thời gian, kỳ ngộ)
        12. Sinh biệt hiệu
        13. Cập nhật thiên địa linh cơ
        14. Cập nhật độ phồn vinh thành phố
        15. Xử lý bộ đếm tương tác còn lại (ví dụ: từ kỳ ngộ)
        16. (Tháng 1 mỗi năm) Cập nhật tính toán quan hệ (quan hệ bậc hai)
        17. (Tháng 1 mỗi năm) Dọn dẹp người chết lâu năm đã bị lãng quên
        18. Lưu trữ và tiến thời gian
        """
        # 0. Cache danh sách nhân vật còn sống trong tháng này
        #    (tái sử dụng trong các giai đoạn sau, được duy trì tại giai đoạn tử vong)
        living_avatars = self.world.avatar_manager.get_living_avatars()

        events: list[Event] = []
        processed_event_ids: set[str] = set()

        # 1. Cập nhật cảm quan & vùng đã biết
        events.extend(self._phase_update_perception_and_knowledge(living_avatars))

        # 2. Suy nghĩ mục tiêu dài hạn
        events.extend(await self._phase_long_term_objective_thinking(living_avatars))

        # 3. Kết toán Gathering
        events.extend(await self._phase_process_gatherings())

        # 4. Giai đoạn ra quyết định
        await self._phase_decide_actions(living_avatars)

        # 5. Giai đoạn commit
        events.extend(self._phase_commit_next_plans(living_avatars))

        # 6. Giai đoạn thực thi
        events.extend(await self._phase_execute_actions(living_avatars))

        # 7. Xử lý bộ đếm tương tác ban đầu
        self._phase_handle_interactions(events, processed_event_ids)

        # 8. Tiến hóa quan hệ
        events.extend(await self._phase_evolve_relations(living_avatars))

        # 9. Kết toán tử vong (Lưu ý: sẽ chỉnh sửa danh sách living_avatars)
        events.extend(self._phase_resolve_death(living_avatars))

        # 10. Tuổi tác và sinh mới
        events.extend(self._phase_update_age_and_birth(living_avatars))

        # 11. Kết toán bị động
        events.extend(await self._phase_passive_effects(living_avatars))

        # 12. Sinh biệt hiệu
        events.extend(await self._phase_nickname_generation(living_avatars))

        # 13. Cập nhật thiên địa linh cơ
        events.extend(self._phase_update_celestial_phenomenon())

        # 14. Cập nhật độ phồn vinh thành phố
        self._phase_update_region_prosperity()

        # 15. Xử lý bộ đếm tương tác còn lại từ các giai đoạn sau
        self._phase_handle_interactions(events, processed_event_ids)

        # 16. (Tháng 1 mỗi năm) Cập nhật tính toán quan hệ (quan hệ bậc hai)
        self._phase_update_calculated_relations(living_avatars)
        
        # 17. (Tháng 1 mỗi năm) Dọn dẹp người chết lâu năm đã bị lãng quên
        if self.world.month_stamp.get_month() == Month.JANUARY:
            cleaned_count = self.world.avatar_manager.cleanup_long_dead_avatars(
                self.world.month_stamp, 
                CONFIG.game.long_dead_cleanup_years
            )
            if cleaned_count > 0:
                # Ghi log, nhưng không tạo sự kiện trong game
                get_logger().logger.info(f"Cleaned up {cleaned_count} long-dead avatars.")

        # 18. Lưu trữ và tiến thời gian
        return self._finalize_step(events)

    def _phase_update_calculated_relations(self, living_avatars: list[Avatar]):
        """
        Làm mới cache quan hệ bậc hai của toàn bộ nhân vật vào tháng 1 mỗi năm
        """
        # Chỉ thực thi vào tháng 1
        if self.world.month_stamp.get_month() != Month.JANUARY:
            return

        for avatar in living_avatars:
            update_second_degree_relations(avatar)

    def _finalize_step(self, events: list[Event]) -> list[Event]:
        """
        Lưu trữ cuối cùng cho bước tiến này:
        loại trùng, ghi vào DB, ghi log, tiến thời gian.
        """
        # 0. Ghi snapshot hàng tháng cho Avatar đang bật theo dõi metrics
        for avatar in self.world.avatar_manager.avatars.values():
            if avatar.enable_metrics_tracking:
                avatar.record_metrics()

        # 1. Loại trùng theo ID (tránh cùng 1 object event bị thêm nhiều lần)
        unique_events: dict[str, Event] = {}
        for e in events:
            if e.id not in unique_events:
                unique_events[e.id] = e
        final_events = list(unique_events.values())

        # 2. Ghi thống nhất vào event manager
        if self.world.event_manager:
            for e in final_events:
                self.world.event_manager.add_event(e)
        
        # 3. Ghi log
        self._phase_log_events(final_events)

        # 4. Tiến thời gian
        self.world.month_stamp = self.world.month_stamp + 1
        
        return final_events
