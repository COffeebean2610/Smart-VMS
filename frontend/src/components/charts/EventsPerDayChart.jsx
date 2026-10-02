import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'Mon', events: 400 },
  { name: 'Tue', events: 300 },
  { name: 'Wed', events: 550 },
  { name: 'Thu', events: 200 },
  { name: 'Fri', events: 700 },
  { name: 'Sat', events: 100 },
  { name: 'Sun', events: 50 },
];

export function EventsPerDayChart() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="name" stroke="#888" />
        <YAxis stroke="#888" />
        <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: '#1f2937', borderColor: '#374151'}} />
        <Bar dataKey="events" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
