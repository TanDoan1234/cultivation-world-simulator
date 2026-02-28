from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.action.cooldown import cooldown_action
from src.classes.event import Event
from src.systems.cultivation import REALM_RANK
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.story_teller import StoryTeller

@cooldown_action
class Retreat(TimedAction):
    """
    Bế quan: Một hành vi mang tính đánh cược.
    Kéo dài ngẫu nhiên từ 1-5 năm.
    Thành công: Nhận được hiệu ứng tăng tỷ lệ đột phá trong vòng 10 năm.
    Thất bại: Bị tổn hao Thọ nguyên.
    """
    
    ACTION_NAME_ID = "retreat_action_name"
    DESC_ID = "retreat_desc"
    REQUIREMENTS_ID = "retreat_requirements"
    
    EMOJI = "🛖"
    PARAMS = {}
    
    # Không thể bế quan lần nữa trong vòng 1 năm sau khi kết thúc bế quan
    ACTION_CD_MONTHS = 12
    IS_MAJOR = True
    
    # Trong thời gian bế quan, không quan tâm thế sự, không vướng nhân quả
    ALLOW_GATHERING = False
    ALLOW_WORLD_EVENTS = False

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        # Thời gian kéo dài ngẫu nhiên: 12 - 60 tháng (1-5 năm)
        self.duration_months = random.randint(12, 60)
    
    def get_save_data(self) -> dict:
        data = super().get_save_data()
        data['duration_months'] = self.duration_months
        return data

    def load_save_data(self, data: dict) -> None:
        super().load_save_data(data)
        if 'duration_months' in data:
            self.duration_months = data['duration_months']

    def calc_success_rate(self) -> float:
        """
        Tính toán tỷ lệ bế quan thành công
        Luyện Khí (0): 50%, Trúc Cơ (1): 40%, Kim Đan (2): 30%, Nguyên Anh (3): 20%
        """
        realm_idx = REALM_RANK.get(self.avatar.cultivation_progress.realm, 0)
        base = 0.5 - (realm_idx * 0.1)
        base = max(0.1, base)
        
        # Áp dụng điểm thưởng từ hiệu ứng (effect)
        extra_rate = self.avatar.effects.get("extra_retreat_success_rate", 0.0)
        return min(1.0, base + float(extra_rate))

    def _execute(self) -> None:
        # _execute của TimedAction được gọi mỗi tháng, ở đây chủ yếu thực hiện kết toán khi kết thúc
        # Nhưng TimedAction.step sẽ chuyển trạng thái thành COMPLETED khi hết thời gian.
        # Chúng ta cần xử lý logic kết toán trong finish, hoặc ở lần step cuối cùng.
        # Theo thiết kế của TimedAction, _execute là logic trong quá trình thực hiện.
        # Chúng ta có thể để trống _execute, hoặc thêm một số sự kiện mô tả tại đây (tùy chọn)
        pass

    async def finish(self) -> list[Event]:
        # 1. Phán định kết quả
        success_rate = self.calc_success_rate()
        is_success = random.random() < success_rate
        
        events = []
        current_month = int(self.world.month_stamp)
        
        if is_success:
            # Thành công: Thêm hiệu ứng tạm thời (10 năm = 120 tháng)
            buff_duration = 120
            # Tăng 30% tỷ lệ đột phá thành công
            bonus = {
                "extra_breakthrough_success_rate": 0.3
            }
            
            self.avatar.temporary_effects.append({
                "source": "Retreat Bonus",
                "effects": bonus,
                "start_month": current_month,
                "duration": buff_duration
            })
            self.avatar.recalc_effects()
            
            result_text = t("retreat_success", duration=self.duration_months)
            core_text = t("{avatar} finished retreat successfully.", avatar=self.avatar.name)
            
            # Tạo cốt truyện
            prompt = t("retreat_story_prompt_success")
            story = await StoryTeller.tell_story(core_text, result_text, self.avatar, prompt=prompt)
            
            events.append(Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True))
            events.append(Event(self.world.month_stamp, story, related_avatars=[self.avatar.id], is_story=True))
            
        else:
            # Thất bại: Khấu trừ thọ nguyên
            # Khấu trừ ngẫu nhiên từ 5-20 năm
            reduce_years = random.randint(5, 20)
            self.avatar.age.decrease_max_lifespan(reduce_years)
            
            # Kiểm tra xem có tử vong không (nếu decrease_max_lifespan dẫn đến tuổi hiện tại vượt mức tối đa,
            # sẽ được phát hiện ở lần cập nhật tuổi hoặc kiểm tra tử vong tiếp theo trong vòng lặp simulator)
            # Chúng ta kiểm tra thủ công ở đây để đưa ra gợi ý
            
            is_dead = self.avatar.age.age >= self.avatar.age.max_lifespan
            
            result_text = t("retreat_fail", reduce_years=reduce_years)
            if is_dead:
                result_text += t("retreat_death_append")
                
            core_text = t("{avatar} failed retreat and lost {years} years of lifespan.", avatar=self.avatar.name, years=reduce_years)
            
            prompt = t("retreat_story_prompt_fail")
            story = await StoryTeller.tell_story(core_text, result_text, self.avatar, prompt=prompt)
            
            events.append(Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True))
            events.append(Event(self.world.month_stamp, story, related_avatars=[self.avatar.id], is_story=True))

        return events

    def can_start(self) -> tuple[bool, str]:
        # Bế quan là hành động tự nguyện, không ràng buộc bởi cảnh giới hay tài nguyên.
        # Cho phép tu sĩ bế quan ngay cả khi thọ nguyên sắp cạn (có thể dẫn đến tử vong trong lúc bế quan).
        # Đây là thiết kế chủ ý để giữ tính rủi ro và ranh giới sinh tử của việc bế quan.
        return True, ""

    def start(self) -> Event:
        # Ghi lại việc bắt đầu
        content = t("retreat_start", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id], is_major=True)
