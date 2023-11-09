import os
import sys
sys.path.append('../..')
import glob
import argparse
import time
from src.utils import *
import torch
import pickle
from src.data_config import *
import transformers
import datetime
import numpy as np
from peft import PeftModel
from transformers import GenerationConfig, LlamaForCausalLM, LlamaTokenizer
import json
from prompter import Prompter

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

try:
    if torch.backends.mps.is_available():
        device = "mps"
except:  # noqa: E722
    pass

answer_list = []

class ASK:
    def __init__(self,
                 load_8bit: bool = False,
                 base_model: str = "",
                 lora_weights: str = "",
                 prompt_template: str = ""):
        base_model = base_model or os.environ.get("BASE_MODEL", "")
        assert (
            base_model
        ), "Please specify a --base_model, e.g. --base_model='huggyllama/llama-7b'"

        self.prompter = Prompter(prompt_template)
        self.tokenizer = LlamaTokenizer.from_pretrained(base_model)

        if device == "cuda":
            model = LlamaForCausalLM.from_pretrained(
                base_model,
                load_in_8bit=load_8bit,
                torch_dtype=torch.float16,
                device_map="auto",
            )
            self.model = PeftModel.from_pretrained(
                model,
                lora_weights,
                torch_dtype=torch.float16,
            ) if lora_weights else model
        elif device == "mps":
            model = LlamaForCausalLM.from_pretrained(
                base_model,
                device_map={"": device},
                torch_dtype=torch.float16,
            )
            self.model = PeftModel.from_pretrained(
                model,
                lora_weights,
                device_map={"": device},
                torch_dtype=torch.float16,
            ) if lora_weights else model
        else:
            model = LlamaForCausalLM.from_pretrained(
                base_model, device_map={"": device}, low_cpu_mem_usage=True
            )
            self.model = PeftModel.from_pretrained(
                model,
                lora_weights,
                device_map={"": device},
            ) if lora_weights else model

        # unwind broken decapoda-research config
        self.model.config.pad_token_id = self.tokenizer.pad_token_id = 0  # unk
        self.model.config.bos_token_id = 1
        self.model.config.eos_token_id = 2

        if not load_8bit:
            self.model.half()  # seems to fix bugs for some users.
    def ask(self,
            instruction,
            input=None,
            temperature=0.1,
            top_p=0.75,
            top_k=40,
            num_beams=4,
            max_new_tokens=1024,
            stream_output=False,
            **kwargs,):

        prompt = self.prompter.generate_prompt(instruction, input)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(device)
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_beams=num_beams,
            **kwargs,
        )

        generate_params = {
            "input_ids": input_ids,
            "generation_config": generation_config,
            "return_dict_in_generate": True,
            "output_scores": True,
            "max_new_tokens": max_new_tokens,
        }

        with torch.no_grad():
            generation_output = self.model.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=max_new_tokens,
            )
        s = generation_output.sequences[0]
        output = self.tokenizer.decode(s)
        time.sleep(1)
        return self.prompter.get_response(output)




prompt_dict = {
    "classify": 'Perform text classification Base on Given long document and classify them into different categories '
               'such as oxygen reduction, oxygen evolution, hydrogen evolution, '
               'CO2 reduction and others.\n '
               '\n=========<abstract>=========',
    "classify_synthesis": "Determine if the following paragraph describes the method of material synthesis,"
                          "the reply should be yes or no.\n"
                          "========<paragraph>=========",
    # "ner": 'Please identify <entity_type> Base on Given long document.\n'
    #        '=========<abstract>=========\n',
    "ner": "Given the following extracted parts of a long document and a question,"
           "Let's think about this logically.\n"
           "Keep the conclusive Answer Explanatory and Holistic."
           "The conclusive Answer Must Base on Given long document.\n"
           "Try to reply a conclusive Answer within five words.\n"
           "<Examples>"
           "QUESTION: what are the <entity_type> in the above text? \n"
           "Material type should be selected one from <material_dict>.\n "
           "Control method type should be selected one from <control_dict>.\n"
           "========<abstract>========="
           "Your REPLY:"
}


def traverse_dir(ask_model, path, prompt, shot, now):

    files = glob.glob(os.path.join(path, "*"))
    if prompt == "classify_synthesis":
        for file_name in files:
            file = open(file_name).readlines()
            for paragraph in file:
                question = prompt_dict[prompt].replace('<paragraph>', paragraph)
                reply = ask_model.ask(question)
                one_data = {"doi":file_name.replace('.txt', ''), "paragraph": paragraph, "reply": reply}
                # answer_list.append({"doi":file_name.replace('.txt', ''), "paragraph": paragraph, "reply": reply})
                with open(args.prompt + args.shot + now + '.json', 'a', encoding='utf8') as fp:
                    json.dump(one_data, fp, ensure_ascii=False, indent=2)
    else:
        for file in files:
            file = open(file).readlines()
            title = file[0].replace('Title:', '')
            abstract = file[2].replace('Abstract:', '')
            question = prompt_dict[prompt].replace('<abstract>', abstract)
            question = question.replace('<entity_type>', ','.join(prompt_key)).replace('<material_dict>',
                                                                                       str(material_dict)).replace(
                '<control_dict>', str(control_dict))
            if shot == 'few':
                context = context_prompt(title, abstract, 2)
                question = question.replace('<Examples>', context)
            else:
                question = question.replace('<Examples>', '')
            print(question)
            reply = ask_model.ask(question)
            one_data = {"title": title, "abstract": abstract, "reply": reply}
            # answer_list.append({"title": title, "abstract": abstract, "reply": reply})
            with open(args.prompt + str(args.lora_weights)[-1] + args.shot + now + '.json', 'a', encoding='utf8') as fp:
                json.dump(one_data, fp, ensure_ascii=False, indent=2)




def context_prompt(input_title, input_abstract, reference_num):
    """
    根据输入的标题和摘要，通过向量匹配的方式进行相似标注文献的提取，
    同时进行上上下文的填充
    :param input_title:
    :param input_abstract:
    :return:
    """

    embedding_data = pickle.load(open('../../embedding_file/embedding', 'rb'))
    entity_data = np.array(pickle.load(open('../../embedding_file/entity', 'rb')))
    title_embedding = encode_with_small_model(input_title)
    abstract_embedding = encode_with_small_model(input_abstract)
    similar_reference_doi = embedding_compare(title_embedding, abstract_embedding, embedding_data, reference_num)
    context = ""
    example_num = 1
    for sdoi in similar_reference_doi:
        similar_reference = entity_data[np.where(entity_data[:, 0] == sdoi)]
        similar_abstract = similar_reference[0][1]
        context += "Example " + str(example_num) + ":\n"
        context += "========" + similar_abstract + "\n"
        context += "========Your REPLY: " + similar_reference[0][2] + "\n"
        example_num += 1
    return context


















if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_model', default=None, type=str)
    parser.add_argument('--lora_weights', default=None, type=str,
                        help="If None, perform inference on the base model")
    parser.add_argument('--load_8bit', action='store_true',
                        help='only use CPU for inference')
    parser.add_argument('--json_path', default=None, type=str)
    parser.add_argument('--prompt', default=None, type=str)
    parser.add_argument('--shot', default='zero', type=str)
    args = parser.parse_args()
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    NewAsk = ASK(args.load_8bit, args.base_model, args.lora_weights, "")
    traverse_dir(NewAsk, args.json_path, args.prompt, args.shot, now)
    # context_prompt('input_title', 'input_abstract', 2)





