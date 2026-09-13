"""
Template-based content generation that works without external APIs
"""
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
import logging

logger = logging.getLogger("ai_survival.tools.template")


class TemplateContentTool(Tool):
    """Generate content from predefined templates without needing external APIs"""

    def __init__(self):
        super().__init__(
            name="template_content",
            description="Generate content from templates (articles, tweets, product descriptions, etc.) without external APIs",
            cost=0.0,
        )

    async def execute(
        self,
        content_type: str,
        topic: str,
        style: str = "professional",
        length: str = "medium",
        affiliate_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate content based on templates"""
        
        templates = {
            "article": self._article_template,
            "tweet": self._tweet_template,
            "linkedin": self._linkedin_template,
            "email": self._email_template,
            "product_description": self._product_template,
            "review": self._review_template,
            "how_to": self._how_to_template,
        }
        
        generator = templates.get(content_type, self._article_template)
        content = generator(topic, style, length)
        
        if affiliate_url:
            content = f"{content}\n\n{affiliate_url}"
        
        return {
            "status": "success",
            "content_type": content_type,
            "topic": topic,
            "content": content,
            "model": "template",
            "real": True,
        }
    
    def _article_template(self, topic: str, style: str, length: str) -> str:
        word_count = {"short": 300, "medium": 600, "long": 1000}.get(length, 600)
        return f"""# {topic.title()}: A {style.title()} Guide

## Introduction
In today's fast-paced world, {topic} has become increasingly important. Whether you're a beginner or an experienced professional, understanding the nuances of {topic} can significantly impact your success.

## Key Points

### 1. Understanding the Basics
{topic} involves several fundamental concepts that every practitioner should know. By mastering these basics, you'll build a solid foundation for more advanced strategies.

### 2. Best Practices
Following industry best practices is essential for success in {topic}. These proven methods have helped thousands achieve their goals.

### 3. Common Mistakes to Avoid
Many people struggle with {topic} because they make preventable errors. Learn from others' experiences and avoid these common pitfalls.

## Conclusion
{topic} offers tremendous opportunities for those who invest time in learning and applying the right strategies. Start implementing these tips today to see results.

---
*This article was generated to help you explore {topic}. Check out our recommended resources below.*
"""
    
    def _tweet_template(self, topic: str, style: str, length: str) -> str:
        hashtags = " #" + " #".join(topic.split()[:3])
        return f"""🚀 {topic.title()} - Essential insights you need to know!

Key takeaways:
✓ Understand the fundamentals
✓ Apply best practices
✓ Avoid common mistakes

Don't miss out! 👇{hashtags}"""
    
    def _linkedin_template(self, topic: str, style: str, length: str) -> str:
        return f"""🎯 {topic.title()}: What I've Learned

After diving deep into {topic}, here are the insights that changed my perspective:

1️⃣ The fundamentals matter more than you think
2️⃣ Consistency beats perfection every time
3️⃣ Learning from mistakes accelerates growth

What's your experience with {topic}? Share in the comments! 👇

#{topic.replace(" ", "")} #ProfessionalDevelopment #Growth"""
    
    def _email_template(self, topic: str, style: str, length: str) -> str:
        return f"""Subject: Quick question about {topic}

Hi there,

I wanted to reach out because {topic} is something I'm really passionate about, and I thought you might find this useful.

I've been exploring some interesting strategies around {topic} lately and would love to hear your thoughts.

Would you be open to a quick chat about it?

Best regards"""
    
    def _product_template(self, topic: str, style: str, length: str) -> str:
        return f"""# {topic.title()} - Premium Quality

## Product Overview
Introducing our premium {topic} solution designed to deliver exceptional results.

## Features
- High-quality materials and construction
- User-friendly design
- Excellent value for money
- Backed by our satisfaction guarantee

## Benefits
✓ Saves you time and effort
✓ Delivers consistent results
✓ Trusted by thousands of customers

## Pricing
 competitive pricing with special discounts available.

Order now and experience the difference!
"""
    
    def _review_template(self, topic: str, style: str, length: str) -> str:
        return f"""# {topic.title()} - Honest Review

## Rating: ★★★★☆ (4/5)

After extensive testing, here's my comprehensive review of {topic}.

### What I Liked
- Excellent performance overall
- Great value for the price
- Easy to use and setup

### What Could Be Better
- Minor improvements needed in documentation
- Could benefit from more features

### Verdict
{topic} is a solid choice for anyone looking for a reliable solution. Highly recommended!

---
*Disclaimer: This review is based on personal experience and testing.*"""
    
    def _how_to_template(self, topic: str, style: str, length: str) -> str:
        return f"""# How to Master {topic.title()}: Step-by-Step Guide

## Prerequisites
Before you begin, make sure you have:
- Basic understanding of the subject
- Required tools and resources
- Dedication to practice

## Step 1: Get Started
Begin by researching the fundamentals of {topic}. Focus on understanding core concepts.

## Step 2: Practice
Apply what you've learned through hands-on practice. Start with simple projects.

## Step 3: Improve
Refine your skills through continuous learning and experimentation.

## Step 4: Master
Share your knowledge with others and continue to advance your expertise in {topic}.

## Conclusion
By following these steps, you'll be well on your way to mastering {topic}. Keep learning and growing!
"""


# Register tool
tool_registry.register(TemplateContentTool())
