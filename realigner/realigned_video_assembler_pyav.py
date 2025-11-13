import os
import sys
import shutil

import pandas as pd
import av

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg
from audio import audio_extractor


def extract_video_segment(input_path, output_path, start_time, end_time, fps):
    """
    Extract a video segment using PyAV
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        start_time: Start time in seconds
        end_time: End time in seconds
        fps: Frame rate for output video
    """
    try:
        input_container = av.open(input_path)
        output_container = av.open(output_path, 'w')
        
        # Get input streams
        input_video_stream = input_container.streams.video[0]
        input_audio_stream = input_container.streams.audio[0] if input_container.streams.audio else None
        
        # Create output streams
        output_video_stream = output_container.add_stream('libx264', rate=fps)
        output_video_stream.width = input_video_stream.width
        output_video_stream.height = input_video_stream.height
        output_video_stream.pix_fmt = 'yuv420p'
        output_video_stream.options = {'crf': '23'}
        
        output_audio_stream = None
        if input_audio_stream:
            output_audio_stream = output_container.add_stream('aac', rate=input_audio_stream.rate)
            output_audio_stream.channels = 2
            output_audio_stream.layout = 'stereo'
            output_audio_stream.bit_rate = 127000
        
        # Seek to start time
        start_pts = int(start_time * input_video_stream.time_base.denominator / input_video_stream.time_base.numerator)
        input_container.seek(start_pts, stream=input_video_stream)
        
        # Process frames
        for packet in input_container.demux(input_video_stream, input_audio_stream):
            if packet.stream.type == 'video':
                for frame in packet.decode():
                    # Check if we've reached the end time
                    frame_time = float(frame.pts * input_video_stream.time_base)
                    if frame_time < start_time:
                        continue
                    if frame_time > end_time:
                        break
                    
                    # Encode and write frame
                    for encoded_packet in output_video_stream.encode(frame):
                        output_container.mux(encoded_packet)
            
            elif packet.stream.type == 'audio' and output_audio_stream:
                for frame in packet.decode():
                    # Check if we've reached the end time
                    frame_time = float(frame.pts * input_audio_stream.time_base)
                    if frame_time < start_time:
                        continue
                    if frame_time > end_time:
                        break
                    
                    # Convert to stereo if needed
                    if frame.layout.name != 'stereo':
                        frame = frame.reformat(layout='stereo')
                    
                    # Encode and write frame
                    for encoded_packet in output_audio_stream.encode(frame):
                        output_container.mux(encoded_packet)
        
        # Flush encoders
        for packet in output_video_stream.encode():
            output_container.mux(packet)
        if output_audio_stream:
            for packet in output_audio_stream.encode():
                output_container.mux(packet)
        
        input_container.close()
        output_container.close()
        return True
        
    except Exception as e:
        print(f"Error extracting segment: {e}")
        return False


def concatenate_videos(video_paths, output_path, fps):
    """
    Concatenate multiple videos using PyAV
    
    Args:
        video_paths: List of paths to input videos
        output_path: Path to output concatenated video
        fps: Frame rate for output video
    """
    try:
        output_container = av.open(output_path, 'w')
        
        # Get properties from first video
        first_container = av.open(video_paths[0])
        first_video_stream = first_container.streams.video[0]
        first_audio_stream = first_container.streams.audio[0] if first_container.streams.audio else None
        
        # Create output streams
        output_video_stream = output_container.add_stream('libx264', rate=fps)
        output_video_stream.width = first_video_stream.width
        output_video_stream.height = first_video_stream.height
        output_video_stream.pix_fmt = 'yuv420p'
        output_video_stream.options = {'crf': '23'}
        
        output_audio_stream = None
        if first_audio_stream:
            output_audio_stream = output_container.add_stream('aac')
            output_audio_stream.channels = 2
            output_audio_stream.layout = 'stereo'
            output_audio_stream.bit_rate = 127000
        
        first_container.close()
        
        # Process each video
        for video_path in video_paths:
            input_container = av.open(video_path)
            input_video_stream = input_container.streams.video[0]
            input_audio_stream = input_container.streams.audio[0] if input_container.streams.audio else None
            
            # Process video frames
            for packet in input_container.demux(input_video_stream):
                for frame in packet.decode():
                    for encoded_packet in output_video_stream.encode(frame):
                        output_container.mux(encoded_packet)
            
            # Process audio frames
            if input_audio_stream and output_audio_stream:
                for packet in input_container.demux(input_audio_stream):
                    for frame in packet.decode():
                        # Convert to stereo if needed
                        if frame.layout.name != 'stereo':
                            frame = frame.reformat(layout='stereo')
                        
                        for encoded_packet in output_audio_stream.encode(frame):
                            output_container.mux(encoded_packet)
            
            input_container.close()
        
        # Flush encoders
        for packet in output_video_stream.encode():
            output_container.mux(packet)
        if output_audio_stream:
            for packet in output_audio_stream.encode():
                output_container.mux(packet)
        
        output_container.close()
        return True
        
    except Exception as e:
        print(f"Error concatenating videos: {e}")
        return False


def extract_videos():
    realignment_df = pd.read_csv(cfg.realignment_timestamps_csv)
    
    for _, df_utt in realignment_df.groupby(["Split", "Dialogue ID", "Utterance ID"]):
        split = df_utt["Split"].values[0]
        dia_id = df_utt["Dialogue ID"].values[0]
        dia_fps = cfg.meld_alt_fps if dia_id in cfg.alt_video_prop_dialogues[split] else cfg.meld_main_fps
        
        # Create single video directory for all videos
        video_folder = cfg.meld_realigned_video_folders[split]
        os.makedirs(video_folder, exist_ok=True)
        
        utt_id = df_utt["Utterance ID"].values[0]
        # Save video directly in the video folder (no subfolders)
        realigned_video_name = os.path.join(video_folder, f"dia{dia_id}_utt{utt_id}.mp4")
        
        if dia_id > 0 and dia_id % 20 == 0 and utt_id == 0:
            print(f"The realigned videos corresponding to the first {dia_id} dialogues of {split} split has been assembled.")
        
        # Create temp folder
        dialogue_tmp_folder = os.path.join(video_folder, f"tmp_dia{dia_id}_utt{utt_id}")
        os.makedirs(dialogue_tmp_folder, exist_ok=True)
        
        orig_dia_ids = df_utt["Original Dialogue ID"].values
        orig_utt_ids = df_utt["Original Utterance ID"].values
        start_timestamps = df_utt["Start Time"].values
        end_timestamps = df_utt["End Time"].values
        
        tmp_video_paths = []
        num_tmp_videos = 0
        
        for odid, ouid, start_ts, end_ts in zip(orig_dia_ids, orig_utt_ids, start_timestamps, end_timestamps):
            raw_video_name = os.path.join(cfg.meld_original_video_folders[split], f"dia{odid}_utt{ouid}.mp4")
            tmp_video_name = os.path.join(dialogue_tmp_folder, f"video_{num_tmp_videos}.mp4")
            
            success = extract_video_segment(raw_video_name, tmp_video_name, start_ts, end_ts, dia_fps)
            
            if success:
                tmp_video_paths.append(tmp_video_name)
                num_tmp_videos += 1
            else:
                raise Exception(f"\t\t\t\tProblems in the creation of {tmp_video_name} out of {raw_video_name}.")
        
        if num_tmp_videos == 0:
            shutil.rmtree(dialogue_tmp_folder)
        elif num_tmp_videos == 1:
            # Just rename if only one segment
            shutil.move(tmp_video_paths[0], realigned_video_name)
            shutil.rmtree(dialogue_tmp_folder)
            # audio_extractor.extract_audio(split, dia_id, [(dia_id, utt_id)], original_meld = False)
        else:
            # Concatenate multiple segments
            success = concatenate_videos(tmp_video_paths, realigned_video_name, dia_fps)
            
            if success:
                shutil.rmtree(dialogue_tmp_folder)
                # audio_extractor.extract_audio(split, dia_id, [(dia_id, utt_id)], original_meld = False)
            else:
                raise Exception(f"\t\t\t\tProblems concatenating videos for the composition of {realigned_video_name}.")


if __name__ == "__main__":
    extract_videos()