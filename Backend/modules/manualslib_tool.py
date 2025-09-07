#!/usr/bin/env python3
"""
Comprehensive test for Manualslib searcher with manual content extraction.
This script tests the search function and extracts detailed information from manuals.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Any
import json

def search_manualslib(query: str) -> str:
    """
    Search Manualslib.com for product manuals.
    Note: Manuals are often PDFs/images, so vision/OCR may be needed to parse content.
   
    Args:
        query: Search term (e.g., "Samsung washing machine manual", "IKEA Malm assembly manual")
    """
    try:
        encoded_query = query.replace(' ', '+')
        # Manualslib search endpoint
        url = f"https://www.manualslib.com/i/{encoded_query}.html"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
       
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
       
        # Parse search results
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        # Look for manual links in search results
        # Manualslib uses different selectors for search results
        manual_links = soup.find_all('a', href=re.compile(r'/manual/\d+/'))
        
        if not manual_links:
            # Try alternative selectors
            manual_links = soup.select('a[href*="/manual/"]')
        
        if not manual_links:
            # Try finding any links that might be manuals
            manual_links = soup.find_all('a', href=True)
            manual_links = [link for link in manual_links if '/manual/' in link.get('href', '')]
        
        for item in manual_links[:5]:  # Get top 5 results
            title = item.get_text(strip=True)
            href = item.get("href")
            
            if href and title:
                # Ensure we have the full URL
                if href.startswith('/'):
                    link = "https://www.manualslib.com" + href
                else:
                    link = href
                
                results.append(f"{title} - {link}")
       
        if not results:
            return f"No Manualslib results found for '{query}'."
       
        return f"Manualslib results for '{query}':\n\n" + "\n".join(results)
   
    except Exception as e:
        return f"Error searching Manualslib: {str(e)}"

class ManualExtractor:
    """Enhanced manual content extractor for Manualslib."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_manual_links(self, search_result: str) -> List[Dict[str, str]]:
        """Extract manual links from search results."""
        manuals = []
        lines = search_result.split('\n')
        
        for line in lines:
            # Look for lines with manual URLs
            if 'https://www.manualslib.com/manual/' in line:
                # Split on the URL pattern
                if ' - https://www.manualslib.com/manual/' in line:
                    parts = line.split(' - https://www.manualslib.com/manual/')
                    if len(parts) == 2:
                        title = parts[0].strip()
                        url = 'https://www.manualslib.com/manual/' + parts[1]
                        manuals.append({'title': title, 'url': url})
                else:
                    # Try to extract title and URL from the line
                    url_match = re.search(r'(https://www\.manualslib\.com/manual/[^\s]+)', line)
                    if url_match:
                        url = url_match.group(1)
                        # Try to get title (everything before the URL)
                        title = line[:url_match.start()].strip(' -')
                        if not title:
                            title = "Manual"
                        manuals.append({'title': title, 'url': url})
        
        return manuals
    
    def extract_manual_details(self, manual_url: str) -> Dict[str, Any]:
        """Extract detailed information from a manual page."""
        try:
            print(f"  → Extracting details from: {manual_url}")
            response = self.session.get(manual_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {
                'url': manual_url,
                'title': self._extract_title(soup),
                'brand': self._extract_brand(soup),
                'model': self._extract_model(soup),
                'category': self._extract_category(soup),
                'manual_type': self._extract_manual_type(soup),
                'pages': self._extract_page_count(soup),
                'file_size': self._extract_file_size(soup),
                'language': self._extract_language(soup),
                'description': self._extract_description(soup),
                'specifications': self._extract_specifications(soup),
                'features': self._extract_features(soup),
                'download_links': self._extract_download_links(soup, manual_url),
                'table_of_contents': self._extract_toc(soup),
                'related_manuals': self._extract_related_manuals(soup),
                'user_rating': self._extract_rating(soup),
                'tags': self._extract_tags(soup)
            }
            
            return details
            
        except Exception as e:
            return {
                'url': manual_url,
                'error': f"Failed to extract details: {str(e)}",
                'title': 'Unknown',
                'extracted': False
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract manual title."""
        # Try multiple selectors for title
        title_selectors = [
            'h1.manual-title',
            'h1',
            '.product-title',
            '.manual-name',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and title != "Manualslib":
                    return title
        
        return "Unknown Title"
    
    def _extract_brand(self, soup: BeautifulSoup) -> str:
        """Extract brand/manufacturer."""
        # Look for brand in various locations
        brand_selectors = [
            '.brand-name', 
            '.manufacturer', 
            '[itemprop="brand"]', 
            '.product-brand',
            '.breadcrumb a'
        ]
        
        for selector in brand_selectors:
            elem = soup.select_one(selector)
            if elem:
                brand = elem.get_text(strip=True)
                if brand and brand.lower() not in ['home', 'manuals', 'manual']:
                    return brand
        
        # Try to extract from title or URL
        title = self._extract_title(soup)
        words = title.split()
        if words:
            # First word is often the brand
            potential_brand = words[0]
            if len(potential_brand) > 2:  # Avoid short words
                return potential_brand
        
        # Try to extract from URL
        url_parts = soup.find('link', {'rel': 'canonical'})
        if url_parts:
            url = url_parts.get('href', '')
            brand_match = re.search(r'/manual/\d+/([^-]+)', url)
            if brand_match:
                return brand_match.group(1).title()
        
        return "Unknown Brand"
    
    def _extract_model(self, soup: BeautifulSoup) -> str:
        """Extract model number."""
        model_selectors = [
            '.model-number', 
            '.product-model', 
            '[itemprop="model"]', 
            '.model'
        ]
        
        for selector in model_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        # Try to find model in title using regex
        title = self._extract_title(soup)
        
        # Look for common model patterns
        model_patterns = [
            r'\b([A-Z0-9-]{3,}(?:\s+[A-Z0-9-]+)*)\b',  # Alphanumeric with dashes
            r'\b([A-Z]+\d+[A-Z0-9-]*)\b',  # Letters followed by numbers
            r'\b(\d+[A-Z]+\d*)\b'  # Numbers with letters
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, title)
            for match in matches:
                if len(match) >= 3 and not match.lower() in ['manual', 'user', 'guide']:
                    return match
        
        # Try extracting from URL
        url_canonical = soup.find('link', {'rel': 'canonical'})
        if url_canonical:
            url = url_canonical.get('href', '')
            model_match = re.search(r'/manual/\d+/[^-]+-(.+)\.html', url)
            if model_match:
                return model_match.group(1).replace('-', ' ').title()
        
        return "Unknown Model"
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """Extract product category."""
        category_selectors = [
            '.category', 
            '.product-category', 
            '.breadcrumb a:not(:first-child):not(:last-child)',
            '[itemprop="category"]'
        ]
        
        for selector in category_selectors:
            elem = soup.select_one(selector)
            if elem:
                category = elem.get_text(strip=True)
                if category and category.lower() not in ['home', 'manuals']:
                    return category
        
        # Try to infer from title
        title = self._extract_title(soup).lower()
        categories = {
            'washing machine': 'Appliances',
            'dishwasher': 'Appliances',
            'refrigerator': 'Appliances',
            'microwave': 'Appliances',
            'furniture': 'Furniture',
            'assembly': 'Furniture',
            'car': 'Automotive',
            'vehicle': 'Automotive',
            'phone': 'Electronics',
            'tablet': 'Electronics',
            'laptop': 'Electronics',
            'computer': 'Electronics'
        }
        
        for keyword, category in categories.items():
            if keyword in title:
                return category
        
        return "Unknown Category"
    
    def _extract_manual_type(self, soup: BeautifulSoup) -> str:
        """Extract type of manual (User Manual, Service Manual, etc.)."""
        title = self._extract_title(soup).lower()
        
        manual_types = [
            ('user manual', 'User Manual'),
            ('user guide', 'User Guide'),
            ('service manual', 'Service Manual'),
            ('installation guide', 'Installation Guide'),
            ('assembly instructions', 'Assembly Instructions'),
            ('assembly manual', 'Assembly Manual'),
            ('quick start', 'Quick Start Guide'),
            ('repair manual', 'Repair Manual'),
            ('operating instructions', 'Operating Instructions'),
            ('technical manual', 'Technical Manual'),
            ('owner', 'Owner Manual')
        ]
        
        for keyword, manual_type in manual_types:
            if keyword in title:
                return manual_type
        
        return "Manual"
    
    def _extract_page_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of pages."""
        # Look for page information in various places
        page_selectors = [
            '.pages', 
            '.page-count',
            '.manual-info',
            '.file-info'
        ]
        
        for selector in page_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text()
                match = re.search(r'(\d+)\s*pages?', text, re.I)
                if match:
                    return int(match.group(1))
        
        # Search entire page text
        page_text = soup.get_text()
        matches = re.findall(r'(\d+)\s*pages?', page_text, re.I)
        
        # Return the most reasonable page count (not too small, not too large)
        for match in matches:
            pages = int(match)
            if 1 <= pages <= 1000:
                return pages
        
        return None
    
    def _extract_file_size(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract file size."""
        size_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(MB|KB|GB)', re.I)
        
        # Look in file info sections first
        info_selectors = ['.file-info', '.manual-info', '.download-info']
        
        for selector in info_selectors:
            elem = soup.select_one(selector)
            if elem:
                match = size_pattern.search(elem.get_text())
                if match:
                    return match.group(0)
        
        # Search entire page
        text = soup.get_text()
        match = size_pattern.search(text)
        return match.group(0) if match else None
    
    def _extract_language(self, soup: BeautifulSoup) -> str:
        """Extract manual language."""
        lang_selectors = [
            '.language', 
            '[lang]', 
            '.manual-language',
            '.file-info'
        ]
        
        for selector in lang_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                lang = elem.get('lang', text)
                if lang and len(lang) > 1:
                    return lang.title()
        
        # Look for language indicators in text
        text = soup.get_text().lower()
        languages = ['english', 'spanish', 'french', 'german', 'italian', 'portuguese']
        
        for lang in languages:
            if lang in text:
                return lang.title()
        
        return "English"  # Default assumption
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract manual description."""
        desc_selectors = [
            '.description', 
            '.manual-description', 
            '.summary', 
            '.product-description',
            '.manual-summary'
        ]
        
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                desc = elem.get_text(strip=True)
                if desc and len(desc) > 20:  # Ensure it's substantial
                    return desc
        
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content', '')
            if content and len(content) > 20:
                return content
        
        return ""
    
    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract product specifications."""
        specs = {}
        
        # Look for specification tables
        spec_tables = soup.find_all('table')
        
        for table in spec_tables:
            # Check if this looks like a specs table
            table_text = table.get_text().lower()
            if any(word in table_text for word in ['specification', 'spec', 'model', 'brand', 'type']):
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value and len(key) < 50 and len(value) < 100:
                            specs[key] = value
        
        # Look for definition lists
        spec_lists = soup.find_all('dl')
        for spec_list in spec_lists:
            terms = spec_list.find_all('dt')
            definitions = spec_list.find_all('dd')
            
            for term, definition in zip(terms, definitions):
                key = term.get_text(strip=True)
                value = definition.get_text(strip=True)
                if key and value and len(key) < 50 and len(value) < 100:
                    specs[key] = value
        
        # Look for key-value pairs in divs
        info_divs = soup.find_all('div', class_=re.compile(r'info|spec|detail', re.I))
        for div in info_divs:
            text = div.get_text()
            # Look for patterns like "Key: Value"
            matches = re.findall(r'([^:]+):\s*([^\n]+)', text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                if key and value and len(key) < 50 and len(value) < 100:
                    specs[key] = value
        
        return specs
    
    def _extract_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features."""
        features = []
        
        # Look for feature lists
        feature_selectors = [
            '.features li', 
            '.feature-list li', 
            '.highlights li', 
            '.key-features li',
            'ul li'
        ]
        
        for selector in feature_selectors:
            elements = soup.select(selector)
            for elem in elements:
                feature = elem.get_text(strip=True)
                if feature and len(feature) > 5 and len(feature) < 200:
                    if feature not in features and not feature.lower().startswith(('home', 'manual', 'download')):
                        features.append(feature)
        
        return features[:10]  # Limit to 10 features
    
    def _extract_download_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract download links for the manual."""
        downloads = []
        
        # Look for PDF download links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        for link in pdf_links:
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href:
                full_url = urljoin(base_url, href)
                downloads.append({
                    'type': 'PDF',
                    'url': full_url,
                    'text': text or 'PDF Download'
                })
        
        # Look for download buttons/links
        download_selectors = [
            '.download a', 
            '.pdf-download a', 
            'a[href*="download"]', 
            'a[href*="pdf"]',
            '.btn-download',
            'a.download'
        ]
        
        for selector in download_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if href and not any(d['url'] == urljoin(base_url, href) for d in downloads):
                    downloads.append({
                        'type': 'Download',
                        'url': urljoin(base_url, href),
                        'text': text or 'Download'
                    })
        
        return downloads
    
    def _extract_toc(self, soup: BeautifulSoup) -> List[str]:
        """Extract table of contents if available."""
        toc = []
        
        toc_selectors = [
            '.table-of-contents li', 
            '.toc li', 
            '.contents li', 
            '.index li',
            '.chapter-list li'
        ]
        
        for selector in toc_selectors:
            elements = soup.select(selector)
            for elem in elements[:10]:  # Limit to first 10 items
                item = elem.get_text(strip=True)
                if item and len(item) > 3 and len(item) < 100:
                    toc.append(item)
        
        return toc
    
    def _extract_related_manuals(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract related manuals."""
        related = []
        
        related_selectors = [
            '.related-manuals a', 
            '.similar-products a',
            '.recommendations a', 
            '.related a',
            'a[href*="/manual/"]'
        ]
        
        for selector in related_selectors:
            links = soup.select(selector)
            for link in links[:5]:  # Limit to 5
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if href and text and '/manual/' in href:
                    full_url = urljoin('https://www.manualslib.com', href)
                    if full_url not in [r['url'] for r in related]:
                        related.append({
                            'title': text,
                            'url': full_url
                        })
        
        return related
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract user rating."""
        rating_selectors = [
            '.rating', 
            '.stars', 
            '.user-rating', 
            '[data-rating]',
            '.score'
        ]
        
        for selector in rating_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Try to find numeric rating in text
                text = elem.get_text()
                match = re.search(r'(\d+(?:\.\d+)?)', text)
                if match:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:  # Assume 5-star rating system
                        return rating
                
                # Try data attribute
                rating_attr = elem.get('data-rating')
                if rating_attr:
                    try:
                        return float(rating_attr)
                    except ValueError:
                        pass
        
        return None
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags/keywords."""
        tags = []
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '').split(',')
            tags.extend([kw.strip() for kw in keywords if kw.strip() and len(kw.strip()) > 2])
        
        # Tag elements
        tag_selectors = [
            '.tags a', 
            '.keywords a', 
            '.labels a',
            '.categories a'
        ]
        
        for selector in tag_selectors:
            elements = soup.select(selector)
            for elem in elements:
                tag = elem.get_text(strip=True)
                if tag and len(tag) > 2 and tag not in tags:
                    tags.append(tag)
        
        return tags[:10]  # Limit to 10 tags

def test_manualslib_search_and_extract():
    """Comprehensive test function."""
    
    print("🔧 Manualslib Search and Extraction Test")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "IKEA Malm assembly manual",
        "Samsung washing machine manual",
        "Toyota Camry service manual",
        "iPhone 13 user manual",
        "Whirlpool dishwasher manual"
    ]
    
    extractor = ManualExtractor()
    all_results = {}
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📋 Test {i}: '{query}'")
        print("-" * 40)
        
        try:
            # Step 1: Search for manuals
            print("🔍 Searching Manualslib...")
            search_result = search_manualslib(query)
            print(f"Search completed. Result length: {len(search_result)} characters")
            
            if "Error searching" in search_result:
                print(f"❌ Search failed: {search_result}")
                all_results[query] = {'error': search_result}
                continue
            
            print(f"📄 Search results preview:\n{search_result[:500]}...")
            
            # Step 2: Extract manual links
            manual_links = extractor.extract_manual_links(search_result)
            print(f"📚 Found {len(manual_links)} manuals")
            
            if not manual_links:
                print("⚠  No manual links found")
                all_results[query] = {'manuals': [], 'search_result': search_result}
                continue
            
            # Print found manual links
            for j, manual in enumerate(manual_links, 1):
                print(f"  {j}. {manual['title']} -> {manual['url']}")
            
            # Step 3: Extract details from first 2 manuals (to avoid overwhelming)
            extracted_manuals = []
            for j, manual in enumerate(manual_links[:2], 1):
                print(f"\n  📖 Extracting manual {j}: {manual['title']}")
                
                details = extractor.extract_manual_details(manual['url'])
                extracted_manuals.append(details)
                
                # Print summary
                if 'error' not in details:
                    print(f"    ✅ Title: {details.get('title', 'N/A')}")
                    print(f"    ✅ Brand: {details.get('brand', 'N/A')}")
                    print(f"    ✅ Model: {details.get('model', 'N/A')}")
                    print(f"    ✅ Type: {details.get('manual_type', 'N/A')}")
                    print(f"    ✅ Pages: {details.get('pages', 'N/A')}")
                    print(f"    ✅ Downloads: {len(details.get('download_links', []))}")
                    print(f"    ✅ Specs: {len(details.get('specifications', {}))}")
                else:
                    print(f"    ❌ {details['error']}")
                
                # Small delay to be respectful
                time.sleep(1)
            
            all_results[query] = {
                'search_result': search_result,
                'manual_count': len(manual_links),
                'manuals': extracted_manuals
            }
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            all_results[query] = {'error': str(e)}
    
    return all_results

def print_detailed_results(results: Dict[str, Any]):
    """Print detailed results in a readable format."""
    
    print("\n" + "=" * 60)
    print("📊 DETAILED EXTRACTION RESULTS")
    print("=" * 60)
    
    for query, data in results.items():
        print(f"\n🔍 QUERY: {query}")
        print("=" * len(query) + "========")
        
        if 'error' in data:
            print(f"❌ Error: {data['error']}")
            continue
        
        if 'manuals' not in data:
            print("⚠  No manual data available")
            continue
        
        for i, manual in enumerate(data['manuals'], 1):
            print(f"\n📖 MANUAL {i}:")
            print("-" * 20)
            
            if 'error' in manual:
                print(f"❌ Error: {manual['error']}")
                continue
            
            # Basic info
            print(f"Title: {manual.get('title', 'N/A')}")
            print(f"Brand: {manual.get('brand', 'N/A')}")
            print(f"Model: {manual.get('model', 'N/A')}")
            print(f"Category: {manual.get('category', 'N/A')}")
            print(f"Type: {manual.get('manual_type', 'N/A')}")
            print(f"Language: {manual.get('language', 'N/A')}")
            print(f"URL: {manual.get('url', 'N/A')}")
            
            # File info
            if manual.get('pages'):
                print(f"Pages: {manual['pages']}")
            if manual.get('file_size'):
                print(f"File Size: {manual['file_size']}")
            
            # Downloads
            downloads = manual.get('download_links', [])
            if downloads:
                print(f"Downloads ({len(downloads)}):")
                for dl in downloads:
                    print(f"  • {dl.get('text', 'Download')}: {dl.get('url', 'N/A')}")
            
            # Specifications
            specs = manual.get('specifications', {})
            if specs:
                print(f"Specifications ({len(specs)}):")
                for key, value in list(specs.items())[:5]:  # Show first 5
                    print(f"  • {key}: {value}")
                if len(specs) > 5:
                    print(f"  ... and {len(specs) - 5} more")
            
            # Features
            features = manual.get('features', [])
            if features:
                print(f"Features ({len(features)}):")
                for feature in features[:3]:  # Show first 3
                    print(f"  • {feature}")
                if len(features) > 3:
                    print(f"  ... and {len(features) - 3} more")
            
            # Table of contents
            toc = manual.get('table_of_contents', [])
            if toc:
                print(f"Table of Contents ({len(toc)} items):")
                for item in toc[:3]:  # Show first 3
                    print(f"  • {item}")
                if len(toc) > 3:
                    print(f"  ... and {len(toc) - 3} more")

def save_results_to_json(results: Dict[str, Any], filename: str = "manualslib_test_results.json"):
    """Save results to JSON file for further analysis."""
    
    print(f"\n💾 Saving results to {filename}...")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Results saved to {filename}")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")

def main():
    """Main test function."""
    
    print("Starting Manualslib comprehensive test...")
    print("This will search for manuals and extract detailed information.")
    print("Please be patient as this may take several minutes.\n")
    
    try:
        # Run the tests
        results = test_manualslib_search_and_extract()
        
        # Print detailed results
        print_detailed_results(results)
        
        # Save to JSON
        save_results_to_json(results)
        
        # Summary
        print(f"\n🎉 TEST COMPLETE!")
        print(f"Processed {len(results)} queries")
        
        success_count = sum(1 for data in results.values() if 'error' not in data)
        print(f"Successful searches: {success_count}/{len(results)}")
        
        total_manuals = sum(len(data.get('manuals', [])) for data in results.values())
        print(f"Total manuals extracted: {total_manuals}")
        
    except KeyboardInterrupt:
        print("\n⚠  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
