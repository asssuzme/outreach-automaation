"""Analyze LinkedIn posts to categorize reposts vs original posts."""
import json
import os
import sys
from pathlib import Path


def analyze_posts(posts_file: str, profile_username: str = None) -> dict:
    """
    Analyze posts data and categorize them.
    
    Args:
        posts_file: Path to posts.json file
        profile_username: LinkedIn username to identify original posts
        
    Returns:
        Dictionary with categorized posts and statistics
    """
    with open(posts_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    # Extract username from first post if not provided
    if not profile_username and posts:
        # Try to get from profile data or infer from author field
        first_post = posts[0]
        if 'author' in first_post:
            profile_username = first_post.get('author', {}).get('username', '')
    
    original_posts = []
    reposts = []
    quote_reposts = []
    
    for post in posts:
        post_type = post.get('post_type', 'unknown')
        author = post.get('author', {})
        author_username = author.get('username', '')
        
        # Determine category
        if post_type == 'quote':
            # Quote repost - user's own repost with commentary
            quote_reposts.append(post)
        elif post_type == 'repost':
            # Direct repost - sharing someone else's post
            reposts.append(post)
        elif post_type == 'regular':
            # Check if it's the user's own post
            if author_username == profile_username or author_username == '':
                original_posts.append(post)
            else:
                # This shouldn't happen but handle edge case
                reposts.append(post)
        else:
            # Unknown type - check author
            if author_username == profile_username:
                original_posts.append(post)
            else:
                reposts.append(post)
    
    # Calculate statistics
    total_posts = len(posts)
    stats = {
        'total_posts': total_posts,
        'original_posts': len(original_posts),
        'reposts': len(reposts),
        'quote_reposts': len(quote_reposts),
        'original_percentage': round(len(original_posts) / total_posts * 100, 1) if total_posts > 0 else 0,
        'repost_percentage': round(len(reposts) / total_posts * 100, 1) if total_posts > 0 else 0,
        'quote_repost_percentage': round(len(quote_reposts) / total_posts * 100, 1) if total_posts > 0 else 0
    }
    
    return {
        'statistics': stats,
        'original_posts': original_posts,
        'reposts': reposts,
        'quote_reposts': quote_reposts,
        'profile_username': profile_username
    }


def save_analysis(analysis: dict, output_file: str):
    """Save analysis results to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"✓ Analysis saved to: {output_file}")


def print_summary(analysis: dict):
    """Print a formatted summary of the analysis."""
    stats = analysis['statistics']
    
    print("\n" + "="*60)
    print("POSTS ANALYSIS SUMMARY")
    print("="*60)
    print(f"Profile: {analysis['profile_username']}")
    print(f"\nTotal Posts: {stats['total_posts']}")
    print(f"\n📝 Original Posts: {stats['original_posts']} ({stats['original_percentage']}%)")
    print(f"🔄 Reposts: {stats['reposts']} ({stats['repost_percentage']}%)")
    print(f"💬 Quote Reposts: {stats['quote_reposts']} ({stats['quote_repost_percentage']}%)")
    print("="*60)
    
    # Show original posts
    if analysis['original_posts']:
        print("\n📝 ORIGINAL POSTS:")
        for i, post in enumerate(analysis['original_posts'], 1):
            posted_at = post.get('posted_at', {}).get('relative', 'Unknown date')
            text = post.get('text', '')[:100] + '...' if len(post.get('text', '')) > 100 else post.get('text', '')
            reactions = post.get('stats', {}).get('total_reactions', 0)
            print(f"  {i}. [{posted_at}] {reactions} reactions")
            print(f"     {text}")
    
    # Show reposts
    if analysis['reposts']:
        print("\n🔄 REPOSTS:")
        for i, post in enumerate(analysis['reposts'], 1):
            posted_at = post.get('posted_at', {}).get('relative', 'Unknown date')
            author = post.get('author', {})
            author_name = f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
            reactions = post.get('stats', {}).get('total_reactions', 0)
            print(f"  {i}. [{posted_at}] Reposted from: {author_name} ({reactions} reactions)")
    
    # Show quote reposts
    if analysis['quote_reposts']:
        print("\n💬 QUOTE REPOSTS (reposts with commentary):")
        for i, post in enumerate(analysis['quote_reposts'], 1):
            posted_at = post.get('posted_at', {}).get('relative', 'Unknown date')
            text = post.get('text', '')[:80] + '...' if len(post.get('text', '')) > 80 else post.get('text', '')
            reshared_post = post.get('reshared_post', {})
            reshared_author = reshared_post.get('author', {})
            reshared_name = f"{reshared_author.get('first_name', '')} {reshared_author.get('last_name', '')}".strip()
            print(f"  {i}. [{posted_at}] Comment: \"{text}\"")
            print(f"     → Reposted from: {reshared_name}")
    
    print("\n" + "="*60)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_posts.py <profile_folder>")
        print("Example: python analyze_posts.py output/jainjatin2525")
        sys.exit(1)
    
    profile_folder = sys.argv[1]
    posts_file = os.path.join(profile_folder, 'posts.json')
    
    if not os.path.exists(posts_file):
        print(f"Error: posts.json not found in {profile_folder}")
        sys.exit(1)
    
    # Extract username from folder name or profile data
    profile_username = os.path.basename(profile_folder)
    
    # Analyze posts
    print(f"Analyzing posts from: {posts_file}")
    analysis = analyze_posts(posts_file, profile_username)
    
    # Save analysis
    analysis_file = os.path.join(profile_folder, 'posts_analysis.json')
    save_analysis(analysis, analysis_file)
    
    # Print summary
    print_summary(analysis)


if __name__ == "__main__":
    main()





