/**
 * Layout plugin to prevent FOUC (Flash of Unstyled Content)
 * This runs only on client-side
 */
export default defineNuxtPlugin({
  name: 'layout',
  setup() {
    if (process.client) {
      // Add html-ready class when app is mounted
      onMounted(() => {
        const nuxtElement = document.getElementById('__nuxt');
        if (nuxtElement) {
          nuxtElement.classList.add('html-ready');
        }
      });
    }
  }
});

