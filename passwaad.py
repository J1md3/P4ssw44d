import itertools
import argparse
import random
import re
import requests
import time
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List
from langdetect import detect, LangDetectException
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

class AdvancedSwahiliGenerator:
    def __init__(self, target_languages: List[str] = ['sw']):
        self.common_symbols = ['!', '@', '#', '$', '%', '.', '*']
        self.num_patterns = ['123', '69', '007', '2023', '2024', '00']
        self.sheng_words = self.load_wordlist('sheng_words.txt')
        self.common_breaches = self.load_wordlist('breach_words.txt')
        self.scraped_swahili = set()
        self.target_languages = target_languages
        self.password_examples = []
        
    def load_wordlist(self, filename: str) -> List[str]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []
        except Exception as e:
            tqdm.write(f"{Fore.RED}Error loading {filename}: {str(e)}")
            return []

    def is_swahili(self, word: str) -> bool:
        try:
            if word.lower() in self.sheng_words or word.lower() in self.common_breaches:
                return False
            lang = detect(word)
            return lang in self.target_languages
        except LangDetectException:
            return False

    def scrape_swahili_words(self, url: str, depth: int, max_depth: int, visited: Set[str]) -> None:
        if depth > max_depth or url in visited:
            return

        try:
            domain = urlparse(url).netloc
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; SwahiliGenerator/2.0)'}
            response = requests.get(url, headers=headers, timeout=15)
            visited.add(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = ' '.join([
                    soup.title.string if soup.title else '',
                    ' '.join([meta.get('content', '') for meta in soup.find_all('meta', {'name': ['description', 'keywords']})]),
                    ' '.join([h.get_text() for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])]),
                    soup.get_text()
                ])
                
                words = re.findall(r'\b[\w\']{3,20}\b', text.lower())
                swahili_words = {word for word in words if self.is_swahili(word)}
                self.scraped_swahili.update(swahili_words)

                if depth < max_depth:
                    links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)
                             if urlparse(urljoin(url, link['href'])).netloc == domain]
                    
                    with tqdm(links, desc=f"{Fore.CYAN}Scanning links", leave=False) as link_bar:
                        for link in link_bar:
                            if link not in visited:
                                self.scrape_swahili_words(link, depth+1, max_depth, visited)

        except Exception as e:
            tqdm.write(f"{Fore.RED}Error scraping {url}: {str(e)}")

    def generate_combinations(self, base_words: List[str], max_combs: int, output_file: str, 
                             urls: List[str] = None, scrape_depth: int = 1, 
                             min_length: int = 8, no_similar: bool = False,
                             custom_symbols: List[str] = None) -> None:
        combinations = set()
        start_time = time.time()
        
        if urls:
            print(f"\n{Fore.YELLOW}=== SWAHILI WORD HARVESTER ===")
            with tqdm(total=len(urls), desc=f"{Fore.BLUE}Scraping Sites", 
                     bar_format="{l_bar}{bar:20}{r_bar}") as site_bar:
                visited = set()
                for url in urls:
                    self.scrape_swahili_words(url, 1, scrape_depth, visited)
                    site_bar.update(1)
                    site_bar.set_postfix({"Words": len(self.scraped_swahili)})

        all_sources = base_words + list(self.scraped_swahili)
        unique_words = list(set([w.lower() for w in all_sources if 3 <= len(w) <= 14]))
        
        print(f"\n{Fore.YELLOW}=== PASSWORD GENERATION ===")
        with open(output_file, 'w', encoding='utf-8') as f, \
             tqdm(total=max_combs, desc=f"{Fore.GREEN}Creating Phrases", 
                  bar_format="{l_bar}{bar:40}{r_bar}") as gen_bar:

            stages = [
                (self.generate_basic_variations, f"{Fore.CYAN}Basic Variations"),
                (self.generate_word_combinations, f"{Fore.MAGENTA}Word Merging"),
                (self.generate_number_combinations, f"{Fore.BLUE}Number Mixing"),
                (self.generate_advanced_combinations, f"{Fore.YELLOW}Advanced Patterns")
            ]

            for generator, stage_name in stages:
                with tqdm(desc=stage_name, leave=False) as stage_bar:
                    for combo in generator(unique_words, no_similar, custom_symbols):
                        if len(combinations) >= max_combs:
                            break
                        
                        if len(combo) < min_length:
                            continue
                            
                        if combo not in combinations:
                            combinations.add(combo)
                            f.write(f"{combo}\n")
                            f.flush()
                            
                            if len(self.password_examples) < 5:
                                self.password_examples.append(combo)
                            
                            gen_bar.update(1)
                            stage_bar.update(1)
                            
                            gen_bar.set_postfix({
                                "examples": self.password_examples[random.randint(0, len(self.password_examples)-1)] if self.password_examples else "",
                                "rate": f"{gen_bar.n / (time.time() - start_time):.1f} pwds/s"
                            })

    def generate_basic_variations(self, words: List[str], no_similar: bool, symbols: List[str]):
        for word in words:
            variants = [word.lower(), word.capitalize()]
            if "'" not in word:
                variants.append(word.upper())
            
            for variant in variants:
                if no_similar:
                    variant = variant.replace('i', '1').replace('o', '0').replace('s', '$')
                yield variant

    def generate_word_combinations(self, words: List[str], no_similar: bool, symbols: List[str]):
        for pair in itertools.permutations(words, 2):
            separators = ['', '_', '.', '-'] if not symbols else symbols
            for sep in separators:
                combo = f"{pair[0].capitalize()}{sep}{pair[1]}"
                if no_similar:
                    combo = combo.replace('i', '1').replace('o', '0').replace('s', '$')
                yield combo

    def generate_number_combinations(self, words: List[str], no_similar: bool, symbols: List[str]):
        symbols = symbols or self.common_symbols
        for word in words:
            for num in self.num_patterns + [str(random.randint(1, 9999))]:
                yield f"{word.capitalize()}{num}"
                yield f"{word}{num}"
                
                if random.random() < 0.7:
                    yield f"{word}{num}{random.choice(symbols)}"
                else:
                    yield f"{random.choice(symbols)}{word}{num}"

    def generate_advanced_combinations(self, words: List[str], no_similar: bool, symbols: List[str]):
        symbols = symbols or self.common_symbols
        for word in words:
            yield f"{word}{random.randint(10000000, 39999999)}"
            
            year = random.randint(1970, 2024)
            yield f"{word}{year}{random.choice(symbols)}"
            
            yield f"{random.choice(symbols)}{word}{random.choice(symbols)}"

def main():
    parser = argparse.ArgumentParser(description="Advanced Swahili Password Generator", add_help=False)
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("-m", "--max", type=int, default=100000, help="Maximum passwords to generate (default: 100000)")
    parser.add_argument("-u", "--url", nargs='+', help="URL(s) to scrape")
    parser.add_argument("-d", "--depth", type=int, help="Scraping recursion depth")
    parser.add_argument("-b", "--base-words", nargs='+', help="Base words for generation")
    parser.add_argument("--min-length", type=int, help="Minimum password length")
    parser.add_argument("--no-similar", action="store_true", help="Exclude similar characters (i→1, o→0)")
    parser.add_argument("--symbols", help="Custom symbols (comma-separated)")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")
    
    args = parser.parse_args()

    if args.help:
        parser.print_help()
        return

    def get_input(prompt: str, default: str = "", required: bool = True):
        while True:
            response = input(f"{Fore.CYAN}{prompt} [{default}]: " if default else f"{Fore.CYAN}{prompt}: ").strip()
            if response:
                return response
            if not required and not response:
                return default
            print(f"{Fore.RED}This field is required.")

    try:
        print(f"{Fore.YELLOW}\n                 p4$$w44d v1.0")
        print(f"{Fore.RED}\nThere's this band called 1023MB.They have'nt had a gig yet") 
        print(r"""
                         
        
   ██▓███    ██████   ██████  █     █░▓█████▄ 
▓██░  ██▒▒██    ▒ ▒██    ▒ ▓█░ █ ░█░▒██▀ ██▌
▓██░ ██▓▒░ ▓██▄   ░ ▓██▄   ▒█░ █ ░█ ░██   █▌
▒██▄█▓▒ ▒  ▒   ██▒  ▒   ██▒░█░ █ ░█ ░▓█▄   ▌
▒██▒ ░  ░▒██████▒▒▒██████▒▒░░██▒██▓ ░▒████▓ 
▒▓▒░ ░  ░▒ ▒▓▒ ▒ ░▒ ▒▓▒ ▒ ░░ ▓░▒ ▒   ▒▒▓  ▒ 
░▒ ░     ░ ░▒  ░ ░░ ░▒  ░ ░  ▒ ░ ░   ░ ▒  ▒ 
░░       ░  ░  ░  ░  ░  ░    ░   ░   ░ ░  ░ 
               ░        ░      ░       ░    
                                     ░      


        """)
        print(r"""
Flag	Description	                Default
-o	    Output file	                passwords.txt
-m	    Max combinations	        100,000
-u	    URLs to scrape	
-d  	Scrape depth	            
-b  	Base words
        """)

        print(f"{Fore.YELLOW}\nUSAGE GUIDE:")

        print(f"{Fore.WHITE}• Run with flags for automation or use interactive mode")

        print(f"{Fore.WHITE}• Example: {Fore.CYAN}passwaad.py -b nairobi -m 100000 -o passwords.txt")

        print(f"{Fore.WHITE}• Use {Fore.CYAN}-h{Fore.WHITE} for full command-line options\n")
 
        print(f"{Fore.YELLOW}\n=== CONFIGURATION ===")
        output_file = args.output or get_input("Output filename", "passwords.txt")
        max_combs = args.max if args.max else int(get_input("Number of passwords to generate", "100000"))
        min_length = args.min_length or int(get_input("Minimum password length", "8"))
        no_similar = args.no_similar or (input(f"{Fore.CYAN}Exclude similar characters? (y/n) [n]: ").lower() == 'y')
        custom_symbols = args.symbols.split(',') if args.symbols else None
        
        if not custom_symbols:
            custom_sym = get_input("Custom symbols (comma-separated)", "!@#$%", required=False)
            custom_symbols = custom_sym.split(',') if custom_sym else None
        
        urls = args.url or input(f"{Fore.CYAN}URLs to scrape (space-separated, enter to skip): ").split()
        depth = 1  # Default value
        
        if urls:
            depth = args.depth or int(get_input("Scraping depth (1-3 recommended)", "1"))
        
        base_words = args.base_words or get_input("Base words (space-separated)").split()

        generator = AdvancedSwahiliGenerator()
        
        print(f"\n{Fore.YELLOW}=== INITIALIZATION ===")
        print(f"{Fore.GREEN}• Local dictionary: {len(generator.sheng_words)} terms")
        print(f"{Fore.GREEN}• Breach patterns: {len(generator.common_breaches)} entries")
        print(f"{Fore.GREEN}• Target count: {max_combs} passwords")
        print(f"{Fore.GREEN}• Min length: {min_length} characters")
        print(f"{Fore.GREEN}• Security level: {'Enhanced' if no_similar else 'Standard'}")
        
        generator.generate_combinations(
            base_words, 
            max_combs, 
            output_file,
            urls=urls if urls else None,
            scrape_depth=depth if urls else 1,
            min_length=min_length,
            no_similar=no_similar,
            custom_symbols=custom_symbols
        )
        
        print(f"\n{Fore.GREEN}✓ Generation complete. Saved to {output_file}")
        print(f"{Fore.CYAN} Run 'wc -l {output_file}' to verify count")
        print(f"{Fore.RED}Made with ❤️ by j1md3! ")

    except Exception as e:
        print(f"\n{Fore.RED}✗ Critical error: {str(e)}")
        print(f"{Fore.YELLOW}⚠ Verify input parameters and dependencies:")
        print("pip install requests beautifulsoup4 tqdm langdetect colorama")

if __name__ == "__main__":
    main()
