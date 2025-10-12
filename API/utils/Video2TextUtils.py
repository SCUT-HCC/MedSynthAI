from funasr import AutoModel

def init_auto_model(model_name):
    return AutoModel(model=model_name,  vad_model="fsmn-vad",  punc_model="ct-punc", 
                    #   spk_model="cam++", 
                      )