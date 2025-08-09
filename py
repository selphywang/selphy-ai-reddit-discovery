import praw
from prawcore.exceptions import ResponseException, RequestException

async def discover_reddit_praw(self) -> List[Dict]:
    """Discover AI tools from Reddit using PRAW (official API)"""
    
    # Check if Reddit credentials exist
    if not os.getenv('REDDIT_CLIENT_ID') or not os.getenv('REDDIT_CLIENT_SECRET'):
        print("⚠️  No Reddit credentials found, skipping Reddit discovery")
        print("   Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env")
        return []
    
    print("🔍 Searching Reddit for AI tools (PRAW)...")
    discoveries = []
    
    try:
        # Initialize PRAW with read-only mode
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'SelphyAI Discovery Bot v1.0')
        )
        reddit.read_only = True  # SAFETY: Can't accidentally post/comment
        
        # The BEST AI tool subreddits
        subreddits_config = {
            'LocalLLaMA': {'sorts': ['hot', 'new', 'top'], 'limit': 30},
            'selfhostedai': {'sorts': ['hot', 'new'], 'limit': 25},
            'singularity': {'sorts': ['hot', 'top'], 'limit': 20},
            'MachineLearning': {'sorts': ['hot', 'new'], 'limit': 20},
            'OpenAI': {'sorts': ['hot', 'new'], 'limit': 20},
            'LangChain': {'sorts': ['hot', 'new'], 'limit': 25},
            'huggingface': {'sorts': ['hot', 'new'], 'limit': 20},
            'comfyui': {'sorts': ['hot', 'new'], 'limit': 15},
            'StableDiffusion': {'sorts': ['hot'], 'limit': 15},
            'ChatGPT': {'sorts': ['hot'], 'limit': 15},
            'ClaudeAI': {'sorts': ['hot', 'new'], 'limit': 15},
            'Oobabooga': {'sorts': ['hot', 'new'], 'limit': 15},
            'ArtificialIntelligence': {'sorts': ['hot'], 'limit': 10},
            'ollama': {'sorts': ['hot', 'new'], 'limit': 20},
        }
        
        # Track what we've seen to avoid duplicates
        seen_repos = set()
        
        for sub_name, config in subreddits_config.items():
            try:
                print(f"  📡 Scanning r/{sub_name}...")
                subreddit = reddit.subreddit(sub_name)
                
                for sort_method in config['sorts']:
                    # Get submissions based on sort method
                    if sort_method == 'hot':
                        submissions = subreddit.hot(limit=config['limit'])
                    elif sort_method == 'new':
                        submissions = subreddit.new(limit=config['limit'])
                    elif sort_method == 'top':
                        submissions = subreddit.top(time_filter='week', limit=config['limit'])
                    else:
                        continue
                    
                    for submission in submissions:
                        # Check URL for GitHub
                        if 'github.com' in submission.url:
                            repo_name = self.extract_repo_name_from_url(submission.url)
                            
                            if repo_name and repo_name not in seen_repos:
                                seen_repos.add(repo_name)
                                
                                discovery = {
                                    'source': 'reddit',
                                    'region': 'global',
                                    'title': repo_name,
                                    'summary': submission.title[:300],  # Reddit titles can be long
                                    'url': submission.url,
                                    'stars': 0,  # Will get from GitHub later
                                    'language': 'Unknown',
                                    'topics': [],
                                    'last_updated': datetime.now().isoformat(),
                                    'created_at': datetime.fromtimestamp(submission.created_utc).isoformat(),
                                    'license': 'Unknown',
                                    'discovered_at': datetime.now().isoformat(),
                                    
                                    # Reddit-specific metadata
                                    'reddit_metadata': {
                                        'subreddit': sub_name,
                                        'upvotes': submission.score,
                                        'upvote_ratio': submission.upvote_ratio,
                                        'num_comments': submission.num_comments,
                                        'reddit_url': f"https://reddit.com{submission.permalink}",
                                        'author': str(submission.author) if submission.author else 'deleted',
                                        'flair': submission.link_flair_text,
                                        'is_video': submission.is_video,
                                        'sort_found': sort_method
                                    }
                                }
                                
                                discoveries.append(discovery)
                                print(f"    ✅ Found: {repo_name} (⬆️{submission.score} in r/{sub_name})")
                        
                        # Also check selftext for GitHub links
                        if hasattr(submission, 'selftext') and submission.selftext:
                            import re
                            github_pattern = r'https?://github\.com/[\w-]+/[\w-]+'
                            github_urls = re.findall(github_pattern, submission.selftext)
                            
                            for gh_url in github_urls[:2]:  # Max 2 per post
                                repo_name = self.extract_repo_name_from_url(gh_url)
                                
                                if repo_name and repo_name not in seen_repos:
                                    seen_repos.add(repo_name)
                                    
                                    discovery = {
                                        'source': 'reddit',
                                        'region': 'global', 
                                        'title': repo_name,
                                        'summary': f"Found in post: {submission.title[:250]}",
                                        'url': gh_url,
                                        'stars': 0,
                                        'language': 'Unknown',
                                        'topics': [],
                                        'last_updated': datetime.now().isoformat(),
                                        'created_at': datetime.fromtimestamp(submission.created_utc).isoformat(),
                                        'license': 'Unknown',
                                        'discovered_at': datetime.now().isoformat(),
                                        
                                        'reddit_metadata': {
                                            'subreddit': sub_name,
                                            'upvotes': submission.score,
                                            'num_comments': submission.num_comments,
                                            'reddit_url': f"https://reddit.com{submission.permalink}",
                                            'author': str(submission.author) if submission.author else 'deleted',
                                            'found_in': 'selftext',
                                            'sort_found': sort_method
                                        }
                                    }
                                    
                                    discoveries.append(discovery)
                                    print(f"    ✅ Found in text: {repo_name}")
                
                # Be nice to Reddit's servers
                await asyncio.sleep(1)
                
            except ResponseException as e:
                print(f"  ⚠️  Reddit API error for r/{sub_name}: {e}")
                continue
            except RequestException as e:
                print(f"  ⚠️  Network error for r/{sub_name}: {e}")
                continue
            except Exception as e:
                print(f"  ❌ Unexpected error for r/{sub_name}: {e}")
                continue
        
        print(f"  📊 Total Reddit discoveries: {len(discoveries)} unique repositories")
        
    except Exception as e:
        print(f"❌ Failed to initialize Reddit API: {e}")
        print("   Check your REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
        return []
    
    return discoveries

def extract_repo_name_from_url(self, github_url: str) -> str:
    """Extract repository name from GitHub URL - bulletproof version"""
    try:
        # Clean the URL
        url = str(github_url).strip()
        
        # Remove common URL fragments
        url = url.split('?')[0]  # Remove query params
        url = url.split('#')[0]  # Remove anchors
        url = url.rstrip('/')     # Remove trailing slash
        
        # Extract GitHub path
        if 'github.com/' in url:
            path = url.split('github.com/')[-1]
            parts = path.split('/')
            
            # Need at least owner/repo
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                
                # Clean repo name (might have .git extension)
                repo = repo.replace('.git', '')
                
                # Validate it's not a GitHub page section
                if owner not in ['features', 'marketplace', 'pricing', 'about']:
                    return repo
                    
    except Exception as e:
        print(f"    ⚠️  Error parsing URL {github_url}: {e}")
    
    return None
