document.addEventListener('DOMContentLoaded', function () {
    const sidebarLinks = document.querySelectorAll('.sidebar-menu-link');
    const articleContainer = document.querySelector('article');

    // Function to load introduction content
    const loadIntroduction = async () => {
        try {
            const response = await fetch('/handbook/introduction/content/');
            if (!response.ok) {
                throw new Error(`Error fetching introduction: ${response.statusText}`);
            }

            const content = await response.text();
            articleContainer.innerHTML = content;

            // Clear URL parameters
            window.history.replaceState(null, null, window.location.pathname);

            // Highlight the Introduction link
            sidebarLinks.forEach((link) => link.classList.remove('active'));
            document.querySelector('#introduction-link').classList.add('active');
        } catch (error) {
            console.error(error);
            articleContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    Failed to load introduction. Please try again later.
                </div>
            `;
        }
    };

    // Function to fetch and load policy details
    const loadPolicyDetails = async (url, updateHash = true) => {
        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (!response.ok) {
                throw new Error(`Error fetching policy details: ${response.statusText}`);
            }

            const data = await response.json();
            if (!data.content || typeof data.content !== 'string') {
                throw new Error("Invalid content received from the server");
            }

            articleContainer.innerHTML = data.content;

            // Scroll to the top of the page
            window.scrollTo({ top: 0 });

            // Reattach event listeners for related policy buttons
            attachRelatedPolicyListeners();

            // Update the hash in the URL
            if (updateHash) {
                const policyId = url.match(/\/policy\/(\d+)\//)?.[1];
                if (policyId) {
                    window.history.replaceState(null, null, `?policy=${policyId}`);
                    updateSidebarState(policyId); // Highlight the correct link and expand details
                }
            }
        } catch (error) {
            console.error(error);
            articleContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    Failed to load policy details. Please try again later.
                </div>
            `;
        }
    };

    // Function to update sidebar state
    const updateSidebarState = (policyId) => {
        sidebarLinks.forEach((link) => {
            link.classList.remove('active');
            const urlPolicyId = link.getAttribute('href')?.match(/\/policy\/(\d+)\//)?.[1];
            if (urlPolicyId === policyId) {
                link.classList.add('active');
                // Expand the parent <details> element
                const details = link.closest('details');
                if (details) {
                    details.open = true;
                }
            }
        });
    };

    // Check if a policy is specified in the URL query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const policyId = urlParams.get('policy');
    if (policyId) {
        // Load the specified policy on page load
        const url = `/handbook/policy/${policyId}/content/`;
        loadPolicyDetails(url, false);
        updateSidebarState(policyId);
    } else {
        // Load the introduction content if no policy is specified
        loadIntroduction();
    }

    // Function to attach event listeners to Related Policies buttons
    const attachRelatedPolicyListeners = () => {
        const relatedPolicyButtons = document.querySelectorAll('.related-policy-btn');
        relatedPolicyButtons.forEach((button) => {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                const url = this.getAttribute('data-policy-url');
                loadPolicyDetails(url);
            });
        });
    };

    // Attach click event listeners to sidebar links
    sidebarLinks.forEach((link) => {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            const isIntroduction = this.hasAttribute('data-introduction');
            if (isIntroduction) {
                loadIntroduction();
            } else {
                const url = this.getAttribute('href');
                loadPolicyDetails(url);
            }
        });
    });

    // Attach listeners for related policies on initial page load
    attachRelatedPolicyListeners();
});
