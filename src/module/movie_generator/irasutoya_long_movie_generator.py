import logging
import os
import sys
import wave

from moviepy.audio.fx.all import audio_loop, volumex
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
)

from ..audio_generator import Audio
from ..manuscript_generator import Manuscript
from .movie_generator import IMovieGenerator

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from util import wrap_text  # noqa: E402

current_dir = os.path.dirname(os.path.abspath(__file__))


class IrasutoyaLongMovieGenerator(IMovieGenerator):
    def __init__(self, id: str, logger: logging.Logger):
        super().__init__(id, is_short=True, logger=logger)

    def generate(self, manuscript: Manuscript, audio: Audio) -> None:
        width, height = 1920, 1080
        font_size = 50

        # 音声を順次結合し、それに合わせて動画を作成する
        video_clips = []
        audio_clips = []
        start_time = 0.0
        total_duration = 0.0
        # irasutoya_movie_generatorでは始めにoverviewを紹介する
        overview_detail = audio.overview_detail
        overview_wav_file_path = overview_detail.wav_file_path
        with wave.open(overview_wav_file_path, "rb") as wav:
            audio_duration = round(wav.getnframes() / wav.getframerate(), 2)
            audio_clip = (
                AudioFileClip(overview_wav_file_path)
                .set_start(start_time)
                .set_duration(audio_duration)
                .fx(volumex, 1.0)
            )
            subtitle_clip = (
                TextClip(
                    manuscript.title,
                    font=self.font_path,
                    fontsize=font_size,
                    color="black",
                )
                .set_position(("center", 800))
                .set_start(start_time)
                .set_duration(audio_duration)
            )
            video_clip = [subtitle_clip]
            video_clips += video_clip
            audio_clips.append(audio_clip)
            start_time += audio_duration
            total_duration += audio_duration

        # 次にcontentsを紹介する
        prev_speaker_image_path = None
        prev_speaker_id = None
        for content_detail in audio.content_details:
            content_transcript = content_detail.transcript
            content_wav_file_path = content_detail.wav_file_path
            # 画像の設定
            if content_detail.speaker_id == prev_speaker_id:
                speaker_image_path = prev_speaker_image_path
            else:
                if content_detail.speaker_gender == "man":
                    speaker_image_path = (
                        self.resource_manager.random_man_character_image_path()
                    )
                    while speaker_image_path == prev_speaker_image_path:
                        speaker_image_path = (
                            self.resource_manager.random_man_character_image_path()
                        )
                else:
                    speaker_image_path = (
                        self.resource_manager.random_woman_character_image_path()
                    )
                    while speaker_image_path == prev_speaker_image_path:
                        speaker_image_path = (
                            self.resource_manager.random_woman_character_image_path()
                        )

            wrapped_texts = wrap_text(content_detail.transcript, width // font_size - 2)
            prev_speaker_image_path = speaker_image_path
            prev_speaker_id = content_detail.speaker_id
            with wave.open(content_wav_file_path, "rb") as wav:
                audio_duration = round(wav.getnframes() / wav.getframerate(), 2)
                audio_clip = (
                    AudioFileClip(content_wav_file_path)
                    .set_start(start_time)
                    .set_duration(audio_duration)
                    .fx(volumex, 1.0)
                )
                subtitle_clips = []
                if len(wrapped_texts) == 1:
                    subtitle_clip = (
                        TextClip(
                            content_transcript,
                            font=self.font_path,
                            fontsize=50,
                            color="black",
                        )
                        .set_position(("center", 800))
                        .set_start(start_time)
                        .set_duration(audio_duration)
                    )
                    subtitle_clips.append(subtitle_clip)
                else:
                    line_height = 70
                    for i, text in enumerate(wrapped_texts):
                        subtitle_clip = (
                            TextClip(
                                text,
                                font=self.font_path,
                                fontsize=font_size,
                                color="black",
                            )
                            .set_start(start_time)
                            .set_duration(audio_duration)
                            .set_position(("center", 700 + line_height * i))
                        )
                        subtitle_clips.append(subtitle_clip)
                white_board_edge_clip = (
                    ColorClip(size=(1840, 450), color=(222, 184, 135))
                    .set_position(("center", "bottom"))
                    .set_start(start_time)
                    .set_duration(audio_duration)
                )
                white_board_clip = (
                    ColorClip(size=(1800, 430), color=(255, 255, 255))
                    .set_position(("center", "bottom"))
                    .set_start(start_time)
                    .set_duration(audio_duration)
                )
                image_clip = (
                    ImageClip(speaker_image_path)
                    .resize(height=500)
                    .set_position(("center", 200))
                    .set_start(start_time)
                    .set_duration(audio_duration)
                )

                video_clip = (
                    [white_board_edge_clip, white_board_clip]
                    + subtitle_clips
                    + [image_clip]
                )
                video_clips += video_clip
                audio_clips.append(audio_clip)
                start_time += audio_duration
                total_duration += audio_duration

        # BGV
        bgv_clip = (
            VideoFileClip(self.resource_manager.random_bgv_path())
            .resize((width, height))
            .loop(duration=total_duration)
        )
        # BGM
        bgm_clip = (
            AudioFileClip(self.resource_manager.random_bgm_path())
            .fx(audio_loop, duration=total_duration)
            .fx(volumex, 0.1)
        )

        # クリップの合成
        video = CompositeVideoClip([bgv_clip] + video_clips)
        audio = CompositeAudioClip([bgm_clip] + audio_clips)
        video = video.set_audio(audio)

        # 動画の保存
        os.remove(self.output_movie_path) if os.path.exists(
            self.output_movie_path
        ) else None
        video.write_videofile(
            self.output_movie_path,
            codec="libx264",
            fps=30,
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
        )

        self.logger.info(
            f"いらすとやを用いた長尺動画を生成しました: {self.output_movie_path}"
        )

        self.upload_manager.register(self.id)

        return
