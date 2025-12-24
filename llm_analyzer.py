"""LLM-based profile analysis module."""
import json
import os
import time
from typing import Dict, Any, List
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


class LLMAnalyzer:
    """Analyze LinkedIn profiles using OpenAI GPT-4."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize LLM Analyzer.
        
        Args:
            api_key: OpenAI API key (defaults to config)
            model: OpenAI model name (defaults to config)
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def load_profile_data(self, profile_dir: str) -> Dict[str, Any]:
        """
        Load all scraped data from profile directory.
        
        Args:
            profile_dir: Directory containing profile data files
            
        Returns:
            Dictionary with all loaded data
        """
        data = {}
        
        # Load profile data
        profile_file = os.path.join(profile_dir, 'profile_data.json')
        if os.path.exists(profile_file):
            with open(profile_file, 'r', encoding='utf-8') as f:
                data['profile'] = json.load(f)
        
        # Load posts data
        posts_file = os.path.join(profile_dir, 'posts.json')
        if os.path.exists(posts_file):
            with open(posts_file, 'r', encoding='utf-8') as f:
                data['posts'] = json.load(f)
        
        # Load posts analysis
        analysis_file = os.path.join(profile_dir, 'posts_analysis.json')
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data['posts_analysis'] = json.load(f)
        
        return data
    
    def create_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """
        Create comprehensive prompt for LLM analysis.
        
        Args:
            data: Dictionary containing profile, posts, and analysis data
            
        Returns:
            Formatted prompt string
        """
        profile = data.get('profile', {})
        posts = data.get('posts', [])
        posts_analysis = data.get('posts_analysis', {})
        
        basic_info = profile.get('basic_info', {})
        experience = profile.get('experience', [])
        
        # Extract key metrics
        original_posts = posts_analysis.get('original_posts', [])
        total_posts = len(posts)
        original_count = len(original_posts)
        
        # Calculate engagement metrics
        total_reactions = 0
        total_comments = 0
        total_reposts = 0
        post_reaction_counts = []
        
        for post in original_posts:
            stats = post.get('stats', {})
            reactions = stats.get('total_reactions', 0)
            comments = stats.get('comments', 0)
            reposts = stats.get('reposts', 0)
            total_reactions += reactions
            total_comments += comments
            total_reposts += reposts
            post_reaction_counts.append(reactions)
        
        avg_reactions = total_reactions / original_count if original_count > 0 else 0
        avg_comments = total_comments / original_count if original_count > 0 else 0
        
        prompt = f"""You are an expert LinkedIn profile analyst working for an Indian marketing agency that helps professionals build their personal brands on LinkedIn, Instagram, Twitter, and other platforms.

Analyze the following LinkedIn profile data and provide a comprehensive assessment:

**PROFILE INFORMATION:**
- Name: {basic_info.get('fullname', 'N/A')}
- Headline: {basic_info.get('headline', 'N/A')}
- Location: {basic_info.get('location', {}).get('full', 'N/A')}
- About/Summary: {basic_info.get('about', 'N/A') or 'Not provided'}
- Connections: {basic_info.get('connection_count', 'N/A')}
- Followers: {basic_info.get('follower_count', 'N/A')}
- Profile URL: {basic_info.get('profile_url', 'N/A')}

**EXPERIENCE:**
{self._format_experience(experience)}

**POSTS ANALYSIS:**
- Total Posts: {total_posts}
- Original Posts: {original_count}
- Average Reactions per Original Post: {avg_reactions:.1f}
- Average Comments per Original Post: {avg_comments:.1f}
- Total Reposts: {total_reposts}

**ORIGINAL POSTS DETAILS:**
{self._format_original_posts(original_posts)}

**ANALYSIS REQUIREMENTS:**

1. **Profile Score** (0-100): Rate overall profile quality based on completeness, professionalism, and engagement potential.

2. **Strengths**: List 3-5 things this profile does well.

3. **Critical Issues**: Identify major problems that significantly impact profile effectiveness:
   - Missing or weak bio/about section
   - Incomplete experience descriptions
   - Low engagement on posts
   - Lack of recommendations
   - Poor headline
   - Any other critical issues

4. **Weaknesses**: List areas for improvement (beyond critical issues).

5. **Engagement Analysis**: Assess post quality, engagement rates, content strategy.

6. **Recommendations**: Provide specific, actionable recommendations for improvement.

7. **Detailed Analysis**: Write a comprehensive 2-3 paragraph analysis covering:
   - Overall profile assessment
   - Content quality and strategy
   - Engagement patterns
   - Areas needing immediate attention
   - Potential for growth

**OUTPUT FORMAT:**
Return your analysis as a valid JSON object with the following structure:
{{
  "profile_score": <0-100>,
  "findings": {{
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "critical_issues": ["issue1", "issue2", ...]
  }},
  "recommendations": ["recommendation1", "recommendation2", ...],
  "engagement_metrics": {{
    "avg_reactions": <number>,
    "avg_comments": <number>,
    "engagement_quality": "<description>",
    "content_strategy_score": <0-100>
  }},
  "detailed_analysis": "<comprehensive analysis text>"
}}

Be honest, direct, and constructive. Focus on actionable insights that would help improve this person's LinkedIn presence."""
        
        return prompt
    
    def _format_experience(self, experience: List[Dict]) -> str:
        """Format experience section for prompt."""
        if not experience:
            return "No experience listed."
        
        formatted = []
        for exp in experience:
            title = exp.get('title', 'N/A')
            company = exp.get('company', 'N/A')
            duration = exp.get('duration', 'N/A')
            description = exp.get('description', '')
            location = exp.get('location', '')
            
            formatted.append(f"- {title} at {company}")
            formatted.append(f"  Duration: {duration}")
            if location:
                formatted.append(f"  Location: {location}")
            formatted.append(f"  Description: {description or 'No description provided'}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_original_posts(self, original_posts: List[Dict]) -> str:
        """Format original posts for prompt."""
        if not original_posts:
            return "No original posts found."
        
        formatted = []
        for i, post in enumerate(original_posts[:10], 1):  # Limit to first 10
            text = post.get('text', '')[:500]  # First 500 chars
            stats = post.get('stats', {})
            posted_at = post.get('posted_at', {}).get('relative', 'N/A')
            
            formatted.append(f"Post {i} ({posted_at}):")
            formatted.append(f"Text: {text}...")
            formatted.append(f"Engagement: {stats.get('total_reactions', 0)} reactions, {stats.get('comments', 0)} comments, {stats.get('reposts', 0)} reposts")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def analyze_profile(self, profile_dir: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Analyze profile using LLM.
        
        Args:
            profile_dir: Directory containing profile data
            max_retries: Maximum number of retry attempts
            
        Returns:
            Analysis results as dictionary
        """
        # Load all data
        data = self.load_profile_data(profile_dir)
        
        # Create prompt
        prompt = self.create_analysis_prompt(data)
        
        # Call OpenAI API with retries
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert LinkedIn profile analyst specializing in personal branding and professional profile optimization. You provide honest, constructive feedback to help professionals improve their LinkedIn presence."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                content = response.choices[0].message.content
                analysis = json.loads(content)
                
                # Add metadata
                analysis['analysis_metadata'] = {
                    'model': self.model,
                    'timestamp': time.time(),
                    'profile_dir': profile_dir
                }
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON response (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception(f"Failed to parse LLM response as JSON: {e}")
            except Exception as e:
                print(f"Error calling OpenAI API (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception(f"Failed to analyze profile after {max_retries} attempts: {e}")
    
    def save_analysis(self, analysis: Dict[str, Any], profile_dir: str) -> str:
        """
        Save analysis results to file.
        
        Args:
            analysis: Analysis results dictionary
            profile_dir: Directory to save analysis
            
        Returns:
            Path to saved file
        """
        filepath = os.path.join(profile_dir, 'analysis_results.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        return filepath


def analyze_profile_with_llm(profile_dir: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a profile directory.
    
    Args:
        profile_dir: Directory containing profile data
        
    Returns:
        Analysis results dictionary
    """
    analyzer = LLMAnalyzer()
    analysis = analyzer.analyze_profile(profile_dir)
    analyzer.save_analysis(analysis, profile_dir)
    return analysis





