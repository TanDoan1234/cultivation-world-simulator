"""
Lớp AI dành cho NPC.
Nơi chứa cơ chế ra quyết định của NPC.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import asyncio

from src.classes.core.world import World
from src.classes.event import Event, NULL_EVENT
from src.utils.llm import call_llm_with_task_name
from src.classes.typings import ACTION_NAME_PARAMS_PAIRS
from src.classes.actions import get_action_infos_str
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

class AI(ABC):
    """
    AI trừu tượng: Sử dụng chung giao diện xử lý hàng loạt (batch).
    """

    @abstractmethod
    async def _decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple]:
        pass

    async def decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str, Event]]:
        """
        Quyết định hành động sẽ làm, đồng thời tạo ra sự kiện tương ứng.
        Vì các lệnh gọi LLM ở tầng dưới đã được đưa vào hàng đợi nhiệm vụ toàn cục, 
        ở đây chỉ cần thực thi đồng thời tất cả các nhiệm vụ.
        """
        # Gọi logic quyết định cụ thể
        results = await self._decide(world, avatars_to_decide)

        # Hoàn thiện trường Event
        for avatar in list(results.keys()):
            action_name_params_pairs, avatar_thinking, short_term_objective = results[avatar]  # type: ignore
            # Không tạo ra sự kiện bắt đầu ở giai đoạn quyết định, mà kích hoạt thống nhất ở giai đoạn commit
            results[avatar] = (action_name_params_pairs, avatar_thinking, short_term_objective, NULL_EVENT)

        return results

class LLMAI(AI):
    """
    LLM AI
    """

    async def _decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str]]:
        """
        Logic quyết định bất đồng bộ: Thông qua LLM để quyết định hành động và tham số thực thi.
        """
        general_action_infos = get_action_infos_str()
        
        async def decide_one(avatar: Avatar):
            # Lấy thông tin thế giới dựa trên khu vực nhân vật đã biết (bao gồm tính toán khoảng cách)
            world_info = world.get_info(avatar=avatar, detailed=True)
            
            # Bao gồm các nhân vật khác nằm trong phạm vi quan sát của nhân vật trong Prompt
            observed = world.get_observable_avatars(avatar)
            avatar_info = avatar.get_expanded_info(co_region_avatars=observed)
            
            info = {
                "avatar_name": avatar.name,
                "avatar_info": avatar_info,
                "world_info": world_info,
                "general_action_infos": general_action_infos,
            }
            template_path = CONFIG.paths.templates / "ai.txt"
            res = await call_llm_with_task_name("action_decision", template_path, info)
            return avatar, res

        # Thực thi đồng thời tất cả các nhiệm vụ
        tasks = [decide_one(avatar) for avatar in avatars_to_decide]
        results_list = await asyncio.gather(*tasks)
        
        results: dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str]] = {}
        for avatar, res in results_list:
            if not res or avatar.name not in res:
                continue
                
            r = res[avatar.name]
            # Chỉ chấp nhận action_name_params_pairs, không hỗ trợ action_name/action_params riêng lẻ nữa
            raw_pairs = r.get("action_name_params_pairs", [])
            pairs: ACTION_NAME_PARAMS_PAIRS = []
            
            for p in raw_pairs:
                if isinstance(p, list) and len(p) == 2:
                    # LLM có thể trả về null cho params, cần chuyển sang dict trống.
                    pairs.append((p[0], p[1] or {}))
                elif isinstance(p, dict) and "action_name" in p and "action_params" in p:
                    pairs.append((p["action_name"], p["action_params"] or {}))
                else:
                    continue
            
            # Phải có ít nhất một hành động
            if not pairs:
                continue # Bỏ qua nếu không tìm thấy hành động hợp lệ

            avatar_thinking = r.get("avatar_thinking", r.get("thinking", ""))
            short_term_objective = r.get("short_term_objective", "")
            
            # Cập nhật cảm xúc
            from src.classes.emotions import EmotionType
            raw_emotion = r.get("current_emotion", "emotion_calm")
            try:
                # Thử lấy enum thông qua value
                avatar.emotion = EmotionType(raw_emotion)
            except ValueError:
                avatar.emotion = EmotionType.CALM
                
            results[avatar] = (pairs, avatar_thinking, short_term_objective)
            
        return results

llm_ai = LLMAI()
