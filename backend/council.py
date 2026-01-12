"""
The LLM Council is a multi-stage reasoning system:

    Multiple LLMs answer the same user query independently
    LLMs anonymously review and rank each other's answers
    A Chairman LLM synthesizes all outputs into a final response
    The user can inspect intermediate model outputs

This approach emphasizes diversity of reasoning, self‑critique, and aggregation of perspectives.
"""
import asyncio
import random
from typing import List, Dict, Tuple
from backend.ollama_client import OllamaClient
from backend.config import COUNCIL_MODELS, CHAIRMAN_MODEL


class CouncilMember:
    """Represents a single LLM in the council"""
    
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url
        self.client = OllamaClient(base_url, model_name)
        self.response = None
        self.rankings = []
    
    async def generate_opinion(self, user_query: str) -> str:
        """Stage 1: Generate initial response to user query"""
        system = (
            "You are a helpful and knowledgeable AI assistant."
            "Provide a thoughtful and accurate response to the user's query."
            "Veracity, accuracy and insight are the top priority. Try to be concise. Consistency is important."
        )
        self.response = await self.client.generate(user_query, system=system)
        return self.response
    
    async def review_responses(
        self,
        user_query: str,
        responses: List[Tuple[str, str]]  # [(anonymous_id, response), ...]
    ) -> List[Dict]:
        """
        Stage 2: Review and rank other responses
        
        Args:
            user_query: Original user question
            responses: List of (anonymous_id, response) tuples
            
        Returns:
            Rankings with explanations
        """
        # Prepare the review prompt
        responses_text = "\n\n".join([
            f"BEGINNING OF RESPONSE {id}:\n{resp}\nEND OF RESPONSE {id}."
            for id, resp in responses
        ])
        
        # Get the list of response IDs
        response_ids = [str(id) for id, _ in responses]
        ids_list = ", ".join(response_ids)
        
        system = (
            "You are a critical evaluator in a council. Review and rank ONLY the responses provided. "
            "Do not invent or reference responses that are not explicitly shown. "
            "Try to be concise and objective in your evaluations."
        )
        
        prompt = f"""Original question: {user_query}

Here are ALL {len(responses)} responses from council members (anonymized):

{responses_text}

IMPORTANT: You must rank ONLY these {len(responses)} responses with IDs: {ids_list}
Do NOT create rankings for any other response IDs.
Provide your ranking and brief justification based on accuracy and insight. Try to be concise.
Consistency is important.

Please rank these responses from best to worst. For each response, provide:
1. The response ID (must be one of: {ids_list})
2. Your score (1-10)
3. Brief justification

Format your answer as:
Response [ID]: [Score]/10 - [Justification]
"""
        
        review = await self.client.generate(prompt, system=system)
        self.rankings.append(review)
        return {"model": self.model_name, "review": review}
    
    async def close(self):
        """Clean up resources"""
        await self.client.close()


class Chairman:
    """The Chairman LLM that synthesizes the final response"""
    
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url
        self.client = OllamaClient(base_url, model_name)
    
    async def synthesize_final_answer(
        self,
        user_query: str,
        council_responses: List[Dict[str, str]],  # [{"model": name, "response": text}, ...]
        reviews: List[Dict[str, str]]  # [{"model": name, "review": text}, ...]
    ) -> str:
        """
        Stage 3: Create final synthesized response
        
        Args:
            user_query: Original user question
            council_responses: All council member responses
            reviews: All reviews from stage 2
            
        Returns:
            Final synthesized answer
        """
        # Prepare context for chairman
        responses_text = "\n\n".join([
            f"Response from {r['model']}:\n{r['response']}"
            for r in council_responses
        ])
        
        reviews_text = "\n\n".join([
            f"Review by {r['model']}:\n{r['review']}"
            for r in reviews
        ])
        
        system = (
            "You are the Chairman of a council. Your role is to synthesize "
            "multiple peer-reviewed answers written by 3 models into a single comprehensive and accurate final answer. "
            "Consider all viewpoints and the reviews provided. Do not add new exclusive information."
        )
        
        prompt = f"""Original question: {user_query}

Council member responses:
{responses_text}

Peer reviews:
{reviews_text}

As Chairman, please synthesize these responses, ranking and reviews into a single 
comprehensive final answer. You should only synthesize responses and not generate your own opinions."""
        
        final_answer = await self.client.generate(prompt, system=system)
        return final_answer
    
    async def close(self):
        """Clean up resources"""
        await self.client.close()


class LLMCouncil:
    """Main orchestrator for the LLM Council workflow"""
    
    def __init__(self):
        self.members = [
            CouncilMember(model["name"], model["url"])
            for model in COUNCIL_MODELS
        ]
        self.chairman = Chairman(CHAIRMAN_MODEL["name"], CHAIRMAN_MODEL["url"])
    
    async def process_query(self, user_query: str, progress_callback=None) -> Dict:
        """
        Execute the full 3-stage council workflow
        
        Args:
            user_query: The user's question
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing all stages of the response
        """
        result = {
            "query": user_query,
            "stage1_responses": [],
            "stage2_reviews": [],
            "stage3_final": ""
        }
        
        # Stage 1: First Opinions - Process sequentially to avoid resource overload
        if progress_callback:
            await progress_callback("stage1", "Gathering initial responses...")
        
        responses = []
        for i, member in enumerate(self.members, 1):
            if progress_callback:
                await progress_callback("stage1", f"Getting response from {member.model_name} ({i}/{len(self.members)})...")
            try:
                response = await member.generate_opinion(user_query)
                responses.append(response)
            except Exception as e:
                if progress_callback:
                    await progress_callback("error", f"Error from {member.model_name}: {str(e)}")
                raise
        
        for member, response in zip(self.members, responses):
            result["stage1_responses"].append({
                "model": member.model_name,
                "response": response
            })
        
        # Stage 2: Review & Ranking
        if progress_callback:
            await progress_callback("stage2", "Council members reviewing responses...")
        
        # Anonymize responses for unbiased review
        anonymous_responses = list(enumerate(responses, 1))
        random.shuffle(anonymous_responses)
        
        review_tasks = [
            member.review_responses(user_query, anonymous_responses)
            for member in self.members
        ]
        reviews = await asyncio.gather(*review_tasks)
        result["stage2_reviews"] = reviews
        
        # Stage 3: Chairman Final Answer
        if progress_callback:
            await progress_callback("stage3", "Chairman synthesizing final answer...")
        
        final_answer = await self.chairman.synthesize_final_answer(
            user_query,
            result["stage1_responses"],
            result["stage2_reviews"]
        )
        result["stage3_final"] = final_answer
        
        return result
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all council members and chairman"""
        checks = {}
        for member in self.members:
            checks[f"council_{member.model_name}"] = await member.client.health_check()
        checks[f"chairman_{self.chairman.model_name}"] = await self.chairman.client.health_check()
        return checks
    
    async def close(self):
        """Clean up all resources"""
        for member in self.members:
            await member.close()
        await self.chairman.close()
