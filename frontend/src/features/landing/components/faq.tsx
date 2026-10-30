import { FAQS } from '../content';

export function Faq() {
  return (
    <section className="sect tint" id="faq" aria-labelledby="faq-h">
      <div className="wrap">
        <div className="sect-h">
          <h2 id="faq-h">Questions</h2>
        </div>
        <div className="faq">
          {FAQS.map(({ question, answer }) => (
            <details key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
