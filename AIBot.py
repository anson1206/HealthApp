from transformers import TextGenerationPipeline, AutoModelForCausalLM, AutoTokenizer

class AIBot:
    def __init__(self, model_name='gpt2'):  # Using GPT-2
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.chatbot = TextGenerationPipeline(model=self.model, tokenizer=self.tokenizer)

    def chat(self, user_input):
        # Refined prompt to direct the model to provide advice
        prompt = f"Provide helpful and scientifically-supported tips for the following question: '{user_input}'. Respond with actionable advice."

        response = self.chatbot(
            prompt,
            max_length=150,  # Keep it short and relevant
            num_return_sequences=1,
            temperature=0.7,  # Control for more focused responses
            top_k=50,
            top_p=0.85,
            repetition_penalty=1.5,
            do_sample=True,
            truncation=True
        )
        return response[0]['generated_text']

if __name__ == "__main__":
    bot = AIBot()
    user_input = "How can I lose weight fast?"
    response = bot.chat(user_input)
    print("Bot:", response)
