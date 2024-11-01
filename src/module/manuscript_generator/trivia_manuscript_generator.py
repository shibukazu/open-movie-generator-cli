import logging
import os
from typing import List

from openai import OpenAI

from .manuscript_generator import IManuscriptGenerator, Manuscript

current_dir = os.path.dirname(os.path.abspath(__file__))


class TriviaManuscriptGenerator(IManuscriptGenerator):
    def __init__(
        self,
        id: str,
        themes: List[str],
        num_trivia: int,
        openai_apikey: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(id, logger)
        self.themes = themes
        self.num_trivia = num_trivia
        try:
            self.openai_client = OpenAI(api_key=openai_apikey)
        except ValueError as e:
            raise e

    def generate(self) -> Manuscript:
        completion = self.openai_client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": f"{','.join(self.themes)}に関する誰も知らないようなトリビアを{self.num_trivia}個生成してください。",
                },
                {
                    "role": "system",
                    "content": "なお、各トリビアはManuscript.content.textに格納してください。",
                },
                {
                    "role": "system",
                    "content": "また、タイトルは15文字以内としてください。",
                },
                {
                    "role": "system",
                    "content": f"また、各トリビアは30文字以内とし、それより多い場合は分割してください。分割した上で{self.num_trivia}個に収まるようにしてください。",
                },
            ],
            response_format=Manuscript,
        )

        manuscript = completion.choices[0].message.parsed
        if not manuscript:
            raise Exception("GPT-4oによる文章生成に失敗しました。")
        manuscript.meta = {
            "type": "pseudo_bulletin_board",
            "themes": self.themes,
        }
        self.logger.debug(manuscript)

        dump = manuscript.model_dump_json()
        with open(self.dump_file_path, "w") as f:
            f.write(dump)
        return manuscript