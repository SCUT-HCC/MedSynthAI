from typing import List, Dict, Tuple, NamedTuple
from ollama import generate
from ollama import GenerateResponse
from Agent.Prompt.AudioFilterPrompt import audio_filter_prompt
from pydub import AudioSegment
from datetime import datetime, timedelta
import os

class TranscriptSegment(NamedTuple):
    speaker: str
    text: str




def split_audio_by_segments(audio_path: str, time_list: List[Dict[str, int]]) -> List[bytes]:
    """
    Split audio file into segments and return binary data for each segment
    
    Args:
        audio_path (str): Path to the audio file
        time_list (List[Dict[str, int]]): List of timing information for each segment
        
    Returns:
        List[bytes]: List of audio segment binary data
    """
    # Load the audio file
    audio = AudioSegment.from_wav(audio_path)
    
    audio_segments = []
    # Split audio for each segment
    for timing in time_list:
        start_ms = timing["start"]
        end_ms = timing["end"]
        
        # Extract the segment
        segment = audio[start_ms:end_ms]
        
        # Export to bytes buffer
        import io
        buffer = io.BytesIO()
        segment.export(buffer, format="wav")
        audio_segments.append(buffer.getvalue())
        
    return audio_segments

async def process_audio_to_text(
    model, 
    audio_path: str, 
    upload_time: datetime = None,
    split_audio: bool = False
) -> Tuple[str, List[TranscriptSegment], List[Dict], List[bytes]]:
    """
    Process audio file to text using FunASR model and format the output
    
    Args:
        model: The FunASR model instance
        audio_path (str): Path to the audio file
        upload_time (datetime): The reference time for calculating absolute timestamps
        split_audio (bool): Whether to split the audio into segments
        
    Returns:
        Tuple[str, List[TranscriptSegment], List[Dict], List[bytes]]: A tuple containing 
            (raw_text, transcript_segments, time_list, audio_segments)
            - raw_text: Original ASR text with speaker markers
            - transcript_segments: List of processed segments with speaker and text
            - time_list: List of timing information for each segment with both relative and absolute times
            - audio_segments: List of audio segment binary data (empty if split_audio=False)
    """
    # Use current time if upload_time is not provided
    if upload_time is None:
        upload_time = datetime.now()
    
    # Generate ASR result
    res = model.generate(
        input=audio_path,
        batch_size_s=300
    )
    
    # Process the result using the new function
    original_text = res[0]["text"]
    
    
    # Process with LLM for correction
    context_text = ""  # Empty context for now
    response: GenerateResponse = generate(
        model='qwen2.5:latest',
        prompt=audio_filter_prompt.format(
            context_text=context_text,
            audio_text=original_text
        )
    )
    
    return response.response